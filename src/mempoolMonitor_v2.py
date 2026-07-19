import argparse
import asyncio
import os
import time
from dataclasses import dataclass

import orjson
from dotenv import load_dotenv
from rich.console import Console
from websockets import connect

from src.analytics.menu import showTitle
from src.marketFilter import filter_target_ids, parse_filters
from src.marketIdMapper import getIdMap, load_market_slugs, saveIdMap
from src.parsers.hex_parser import parse_calldata
from src.place_orders import BUY_limit_order, init_client
from src.types import (
    IdMap,
    Metadata,
    Trades,
    Transaction,
    init_trade,
    save_metadata,
    save_trades,
)
from src.utils.main import (
    clear_console,
    get_start_timestamp,
    getAllPositionsValue,
    getBalance,
)
from src.utils.jsonHelper import saveAsJSON


load_dotenv()

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY") or ""
WSS_URL = f"wss://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

DEFAULT_WALLET = "0xf3531b23b504cf0aed4ff21325232b2a2d496685"
MY_WALLET = os.getenv("WALLET") or ""

CTF_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"
METHOD_ID = "0x3c2b4399"
DEFAULT_TIME = 300

INCOMING_QUEUE_SIZE = 10_000
SIGNAL_QUEUE_SIZE = 1_000
MY_TRADE_LOGS_PATH = "./data/my_trade_logs"

console = Console(
    log_time_format=lambda dt: f"[{dt.strftime('%H:%M:%S.%f')[:-3]}]"
)


@dataclass(slots=True)
class PendingTransaction:
    tx_data: dict
    received_at: float
    received_ns: int


@dataclass(slots=True)
class TradeSignal:
    tx_hash: str
    transaction: Transaction
    received_at: float
    received_ns: int
    parsed_ns: int


@dataclass
class MyTrade:
    """An accepted copy order linked to the target transaction that triggered it."""

    target_tx_hash: str
    target_wallet: str
    token_id: str

    target_shares: float
    target_usdc_amount: float
    target_price_per_share: float

    order_id: str
    order_status: str
    my_shares: float
    my_usdc_amount: float
    my_price_per_share: float
    price_difference: float

    trade_ids: tuple[str, ...]
    transaction_hashes: tuple[str, ...]
    submitted_at: float
    response_at: float
    latency_ms: float


@dataclass(slots=True)
class PipelineStats:
    websocket_messages: int = 0
    candidates: int = 0
    parsed_trades: int = 0
    dropped_candidates: int = 0
    reconnects: int = 0
    parse_attempts: int = 0
    total_parse_ns: int = 0
    total_order_ns: int = 0
    orders_submitted: int = 0

    def display(self) -> None:
        avg_parse_us = (
            self.total_parse_ns / self.parse_attempts / 1_000
            if self.parse_attempts
            else 0.0
        )
        avg_order_ms = (
            self.total_order_ns / self.orders_submitted / 1_000_000
            if self.orders_submitted
            else 0.0
        )
        console.log(
            "Pipeline stats | "
            f"messages={self.websocket_messages:,} | "
            f"candidates={self.candidates:,} | "
            f"trades={self.parsed_trades:,} | "
            f"dropped={self.dropped_candidates:,} | "
            f"reconnects={self.reconnects:,} | "
            f"avg parse={avg_parse_us:.1f}µs | "
            f"avg order={avg_order_ms:.1f}ms"
        )


class MempoolMonitor:
    def __init__(
        self,
        wallet: str,
        id_map: IdMap,
        filter_ids: set[str] | None,
        client,
        is_activated: bool,
    ):
        self.wallet = wallet.lower()
        self.wallet_padded = f"{'0' * 24}{self.wallet[2:]}"
        self.id_map = id_map
        self.filter_ids = filter_ids
        self.client = client
        self.is_activated = is_activated

        self.seen_txs: set[str] = set()
        self.trades: Trades = {}
        self.my_trades: dict[str, MyTrade] = {}
        self.factor = 10

        # Avoid hexadecimal-to-decimal conversion in the order hot path.
        self.decimal_token_ids = {
            token_id: str(int(token_id, 16)) for token_id in id_map
        }

    def parse_transaction(
        self, pending: PendingTransaction, stats: PipelineStats
    ) -> TradeSignal | None:
        tx_hash = pending.tx_data.get("hash", "")
        if not tx_hash or tx_hash in self.seen_txs:
            return None
        self.seen_txs.add(tx_hash)

        parse_started_ns = time.perf_counter_ns()
        transaction = parse_calldata(pending.tx_data.get("input", ""), self.wallet)
        parsed_ns = time.perf_counter_ns()
        stats.parse_attempts += 1
        stats.total_parse_ns += parsed_ns - parse_started_ns

        if transaction is None:
            return None

        token_id = transaction.token_id
        if self.filter_ids is not None and token_id not in self.filter_ids:
            return None

        stats.parsed_trades += 1
        return TradeSignal(
            tx_hash=tx_hash,
            transaction=transaction,
            received_at=pending.received_at,
            received_ns=pending.received_ns,
            parsed_ns=parsed_ns,
        )

    async def buy(self, token_id: str, shares: float):
        buy_token_id = self.decimal_token_ids.get(token_id)
        if buy_token_id is None:
            buy_token_id = str(int(token_id, 16))
        buy_shares = str(shares / self.factor)
        return await BUY_limit_order(self.client, buy_token_id, "0.9", buy_shares)

    def record_my_trade(
        self,
        signal: TradeSignal,
        response,
        submitted_at: float,
        response_at: float,
        latency_ms: float,
    ) -> MyTrade:
        my_usdc_amount = float(response.making_amount)
        my_shares = float(response.taking_amount)
        my_price = my_usdc_amount / my_shares if my_shares else 0.0

        target = signal.transaction
        target_price = target.usdc_amount / target.shares if target.shares else 0.0

        my_trade = MyTrade(
            target_tx_hash=signal.tx_hash,
            target_wallet=target.wallet,
            token_id=target.token_id,
            target_shares=target.shares,
            target_usdc_amount=target.usdc_amount,
            target_price_per_share=target_price,
            order_id=response.order_id,
            order_status=response.status,
            my_shares=my_shares,
            my_usdc_amount=my_usdc_amount,
            my_price_per_share=my_price,
            price_difference=my_price - target_price,
            trade_ids=tuple(response.trade_ids),
            transaction_hashes=tuple(str(tx_hash) for tx_hash in response.transactions_hashes),
            submitted_at=submitted_at,
            response_at=response_at,
            latency_ms=latency_ms,
        )
        self.my_trades[signal.tx_hash] = my_trade
        return my_trade


def save_my_trades(my_trades: dict[str, MyTrade], start_timestamp: int) -> str:
    os.makedirs(MY_TRADE_LOGS_PATH, exist_ok=True)
    path = f"{MY_TRADE_LOGS_PATH}/{start_timestamp}-my-trades.json"
    saveAsJSON(my_trades, path)
    return path


def _subscription() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_subscribe",
        "params": [
            "alchemy_pendingTransactions",
            {"toAddress": CTF_EXCHANGE},
        ],
    }


async def websocket_reader(
    monitor: MempoolMonitor,
    incoming_queue: asyncio.Queue,
    start_ns: int,
    deadline_ns: int,
    stats: PipelineStats,
) -> None:
    """Continuously drain the websocket and enqueue only cheap-match candidates."""
    first_connection = True

    while time.perf_counter_ns() < deadline_ns:
        try:
            async with connect(WSS_URL, max_queue=4_096) as websocket:
                await websocket.send(orjson.dumps(_subscription()))
                await websocket.recv()

                if first_connection:
                    console.log("Subscribed to pending transactions")
                    first_connection = False
                else:
                    stats.reconnects += 1
                    console.log("Reconnected to pending transactions")

                while True:
                    remaining = (deadline_ns - time.perf_counter_ns()) / 1_000_000_000
                    if remaining <= 0:
                        return

                    try:
                        message = await asyncio.wait_for(websocket.recv(), remaining)
                    except TimeoutError:
                        return

                    received_ns = time.perf_counter_ns()
                    if received_ns < start_ns:
                        continue

                    stats.websocket_messages += 1
                    data = orjson.loads(message)
                    result = data.get("params", {}).get("result")
                    if not isinstance(result, dict):
                        continue

                    hex_data = result.get("input", "")
                    if not isinstance(hex_data, str):
                        continue
                    if hex_data[: len(METHOD_ID)].lower() != METHOD_ID:
                        continue
                    if monitor.wallet_padded not in hex_data.lower():
                        continue

                    stats.candidates += 1
                    pending = PendingTransaction(
                        tx_data=result,
                        received_at=time.time(),
                        received_ns=received_ns,
                    )
                    try:
                        incoming_queue.put_nowait(pending)
                    except asyncio.QueueFull:
                        stats.dropped_candidates += 1
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if time.perf_counter_ns() >= deadline_ns:
                return
            console.log(f"[bold red]Websocket disconnected:[/] {error}")
            await asyncio.sleep(0.25)


async def parser_worker(
    monitor: MempoolMonitor,
    incoming_queue: asyncio.Queue,
    order_queue: asyncio.Queue | None,
    analytics_queue: asyncio.Queue,
    stats: PipelineStats,
) -> None:
    while True:
        pending = await incoming_queue.get()
        try:
            if pending is None:
                return

            # Keep synchronous calldata decoding off the websocket event loop.
            signal = await asyncio.to_thread(monitor.parse_transaction, pending, stats)
            if signal is None:
                continue

            # Dispatch orders first. Analytics must never delay live execution.
            if (
                order_queue is not None
                and signal.transaction.action == "BUY"
            ):
                await order_queue.put(signal)
            await analytics_queue.put(signal)
        except Exception:
            console.print_exception()
        finally:
            incoming_queue.task_done()


async def order_worker(
    monitor: MempoolMonitor,
    order_queue: asyncio.Queue,
    stats: PipelineStats,
    start_timestamp: int,
) -> None:
    """Submit orders sequentially so balance and exposure decisions remain ordered."""
    while True:
        signal = await order_queue.get()
        try:
            if signal is None:
                return

            submitted_at = time.time()
            order_started_ns = time.perf_counter_ns()
            response = await monitor.buy(
                signal.transaction.token_id,
                signal.transaction.shares,
            )
            order_finished_ns = time.perf_counter_ns()
            response_at = time.time()
            order_duration_ns = order_finished_ns - order_started_ns
            stats.total_order_ns += order_duration_ns
            stats.orders_submitted += 1
            await asyncio.to_thread(console.log, response)

            if not response.ok:
                continue

            my_trade = monitor.record_my_trade(
                signal,
                response,
                submitted_at,
                response_at,
                order_duration_ns / 1_000_000,
            )
            await asyncio.to_thread(
                console.log,
                "Price comparison | "
                f"target=[bold cyan]{my_trade.target_price_per_share * 100:.2f}¢[/] | "
                f"mine=[bold yellow]{my_trade.my_price_per_share * 100:.2f}¢[/] | "
                f"difference=[bold]{my_trade.price_difference * 100:+.2f}¢[/]",
            )
            # Persist accepted orders immediately so an unexpected shutdown does not
            # lose the link between our order and its source transaction.
            await asyncio.to_thread(
                save_my_trades,
                monitor.my_trades,
                start_timestamp,
            )
        except Exception:
            console.print_exception()
        finally:
            order_queue.task_done()


async def analytics_worker(
    monitor: MempoolMonitor,
    analytics_queue: asyncio.Queue,
) -> None:
    while True:
        signal = await analytics_queue.get()
        try:
            if signal is None:
                return

            trade = init_trade(
                signal.tx_hash,
                signal.transaction,
                monitor.id_map,
                signal.received_at,
            )
            monitor.trades[signal.tx_hash] = trade
            # Rich output can block on the terminal, so render it outside the event loop.
            await asyncio.to_thread(trade.display)
        except Exception:
            console.print_exception()
        finally:
            analytics_queue.task_done()


async def run_pipeline(
    monitor: MempoolMonitor,
    start_timestamp: int,
    runtime: int,
    stats: PipelineStats,
) -> int:
    incoming_queue = asyncio.Queue(maxsize=INCOMING_QUEUE_SIZE)
    analytics_queue = asyncio.Queue(maxsize=SIGNAL_QUEUE_SIZE)
    order_queue = (
        asyncio.Queue(maxsize=SIGNAL_QUEUE_SIZE) if monitor.is_activated else None
    )

    delay_seconds = max(0.0, start_timestamp - time.time())
    start_ns = time.perf_counter_ns() + int(delay_seconds * 1_000_000_000)
    deadline_ns = start_ns + runtime * 1_000_000_000

    parser_task = asyncio.create_task(
        parser_worker(
            monitor,
            incoming_queue,
            order_queue,
            analytics_queue,
            stats,
        ),
        name="mempool-parser",
    )
    analytics_task = asyncio.create_task(
        analytics_worker(monitor, analytics_queue),
        name="mempool-analytics",
    )
    order_task = (
        asyncio.create_task(
            order_worker(monitor, order_queue, stats, start_timestamp),
            name="mempool-order-executor",
        )
        if order_queue is not None
        else None
    )

    try:
        await websocket_reader(
            monitor,
            incoming_queue,
            start_ns,
            deadline_ns,
            stats,
        )

        await incoming_queue.join()
        await incoming_queue.put(None)
        await parser_task

        if order_queue is not None and order_task is not None:
            await order_queue.join()
            await order_queue.put(None)
            await order_task

        await analytics_queue.join()
        await analytics_queue.put(None)
        await analytics_task
    finally:
        tasks = [parser_task, analytics_task]
        if order_task is not None:
            tasks.append(order_task)
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return int(time.time())


def shutdown(
    monitor: MempoolMonitor | None,
    start_timestamp: int,
    end_timestamp: int | None,
    market_filter: str,
    save_logs: bool,
) -> None:
    end_timestamp = end_timestamp or int(time.time())
    if monitor is not None and save_logs:
        id_map_path = saveIdMap(monitor.id_map, start_timestamp)
        logs_path = save_trades(monitor.trades, start_timestamp)
        metadata = Metadata(
            start_timestamp,
            end_timestamp,
            monitor.wallet,
            market_filter,
            id_map_path,
            logs_path,
        )
        save_metadata(metadata, start_timestamp)
    console.log("Shutting down now...")


async def monitor_trades() -> None:
    clear_console()

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--runtime", type=int, default=DEFAULT_TIME)
    parser.add_argument("-s", "--start_time", help="Scheduled start time")
    parser.add_argument("-w", "--wallet", default=DEFAULT_WALLET)
    parser.add_argument(
        "-f",
        "--filter",
        default="",
        help="Filter format 'market_name/market_type;market_name/market_type'",
    )
    parser.add_argument("--logs", action="store_true", help="Save session logs")
    parser.add_argument(
        "--activate",
        action="store_true",
        help="WARNING: use real money for Polymarket orders",
    )
    args = parser.parse_args()

    showTitle("Mempool monitor v2", "bold yellow")

    start_timestamp = int(time.time())
    if args.start_time:
        start_timestamp = get_start_timestamp(args.start_time)
        if start_timestamp < time.time():
            raise ValueError("Invalid starting time! Adjust or deactivate scheduled start")

    console.log(f"Monitoring trades from: {args.wallet}")
    console.log(f"Wallet balance: ${getBalance(args.wallet):,.2f}")
    console.log(f"Positions value: ${getAllPositionsValue(args.wallet):,.2f}")
    console.log(f"Expected runtime: {args.runtime} seconds")
    if args.start_time:
        console.log(f"Scheduled start at: {args.start_time}")

    filters = parse_filters(args.filter) if args.filter else None
    slugs = load_market_slugs(start_timestamp, start_timestamp + args.runtime)
    id_map = getIdMap(slugs)
    filter_ids = filter_target_ids(id_map, filters) if filters else None
    console.log("[bold green]Fetched market ID map[/]")

    client = None
    if args.activate:
        console.log("[bold red]WARNING: copy trading is active; real money will be used[/]")
        console.log(f"Your wallet balance: ${getBalance(MY_WALLET):,.2f}")
        client = await init_client()
    else:
        console.log("[bold yellow]Copy trading is not activated[/]")

    monitor = MempoolMonitor(
        args.wallet,
        id_map,
        filter_ids,
        client,
        args.activate,
    )
    stats = PipelineStats()
    end_timestamp = None

    try:
        end_timestamp = await run_pipeline(
            monitor,
            start_timestamp,
            args.runtime,
            stats,
        )
    finally:
        stats.display()
        shutdown(
            monitor,
            start_timestamp,
            end_timestamp,
            args.filter,
            args.logs,
        )


if __name__ == "__main__":
    try:
        asyncio.run(monitor_trades())
    except KeyboardInterrupt:
        pass
