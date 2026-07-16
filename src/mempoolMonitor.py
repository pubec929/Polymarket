from web3 import Web3
from websockets import connect
import asyncio
import orjson
import time
from datetime import datetime

from typing import Set, Dict

from dotenv import load_dotenv
import os
import sys
import argparse
import questionary

from src.marketIdMapper import getIdMap, load_market_slugs, saveIdMap, getLastTimestamp, getFilePath
from src.types import IdMap, Trades, init_trade, Metadata, save_metadata, save_trades

from src.utils.main import getAllPositionsValue, getBalance, get_start_timestamp, clear_console
from src.marketFilter import filter_target_ids, parse_filters
from src.analytics.menu import showTitle
from src.parsers.hex_parser import parse_calldata
from src.place_orders import init_client, BUY_limit_order

from rich.console import Console

load_dotenv()

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY") or ""
WSS_URL = f"wss://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

DEFAULT_WALLET = "0xf3531b23b504cf0aed4ff21325232b2a2d496685"

# Polymarket contract addresses
CTF_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"

METHOD_ID = "0x3c2b4399"

DEFAULT_TIME = 300

MY_WALLET = os.getenv("WALLET") or ""

console = Console(log_time_format = lambda dt: f"[{dt.strftime("%H:%M:%S.%f")[:-3]}]") # type: ignore

class MempoolMonitor:
    def __init__(self, wallet: str, id_map: IdMap, filter_ids: set[str] | None, client, is_activated):
        self.wallet = wallet.lower()
        self.id_map = id_map
        self.known_token_ids = set(id_map.keys())
        
        self.seen_txs: Set[str] = set()
        self.trades: Trades = {}

        self.active_filter = bool(filter_ids)
        self.filter_ids = filter_ids

        self.client = client

        self.is_activated = is_activated
        self.factor = 10
    async def process_pending_transaction(self, tx_data: Dict):
        """Process a pending (mempool) transaction"""
        
        detection_time = time.time()
        
        try:
            tx_hash = tx_data.get('hash', "")
            hex_data = tx_data.get('input', '')
            
            # Quick filters
            if tx_hash in self.seen_txs:
                return
            else:
                self.seen_txs.add(tx_hash)
            
            # Check function signature
            if not hex_data or len(hex_data) < 10:
                return
            
            if hex_data[:len(METHOD_ID)] != METHOD_ID:
                return
            
            wallet_padded = f"000000000000000000000000{self.wallet[2:]}"
            if wallet_padded not in hex_data: # normally the target id sits in the ninth chunk
                return
           
            # Try to extract token ID
            transaction = parse_calldata(hex_data, self.wallet)
            if not transaction:
                print(f"⚠️  Could not decode transaction: {tx_hash}...")
                return 

            token_id = transaction.token_id
            
            if self.is_activated:
                await self.buy(token_id, transaction.shares)
            if self.active_filter and token_id not in self.filter_ids:
                print("filtered out", self.id_map[token_id].question if token_id in self.id_map else "Unknow market")
                return
            
            trade = init_trade(tx_hash, transaction, self.id_map, detection_time)
            trade.display()
            self.trades[tx_hash] = trade
            sys.exit()
        except Exception as e:
            print(f"❌ Error processing pending tx: {e}")
            import traceback
            traceback.print_exc()

    async def buy(self, token_id: str, shares: float):
        buy_token_id = str(int(token_id, 16))
        buy_shares = str(shares / self.factor)
        response = await BUY_limit_order(self.client, buy_token_id, "0.9", buy_shares)
        console.log(response)
        # todo save transaction


def shutdown(monitor: MempoolMonitor | None, start_timestamp: int, end_timestamp: int | None, market_filter: str, save_logs: bool):
    end_timestamp = end_timestamp or int(time.time())
    if monitor:
        if save_logs:
            id_map_path = saveIdMap(monitor.id_map, start_timestamp)
            logs_path = save_trades(monitor.trades, start_timestamp)
            metadata = Metadata(start_timestamp, end_timestamp, monitor.wallet, market_filter, id_map_path, logs_path)
            save_metadata(metadata, start_timestamp)
    console.log("shutting down now...")

async def monitor_trades():
    clear_console()

    parser = argparse.ArgumentParser()

    parser.add_argument("-r", "--runtime", type=int, default=DEFAULT_TIME, help="Runtime duration in seconds")
    parser.add_argument("-s", "--start_time", help="start time of the mempool monitor")
    parser.add_argument("-w", "--wallet", default=DEFAULT_WALLET, help="the specified target wallet")
    parser.add_argument("-f", "--filter", default="", help="Filter format 'market_name/market_type;market_name/market_type'")
    parser.add_argument("--logs", help="save logs after execution", action="store_true")
    parser.add_argument("--activate", help="Warning!!!Uses real money for polymarket bets. Use with caution", action="store_true")
    args = parser.parse_args()

    runtime: int = args.runtime
    start_time: str = args.start_time
    wallet: str = args.wallet
    market_filter: str = args.filter
    is_save_logs: bool = args.logs
    is_activated: bool = args.activate

    filters = parse_filters(market_filter) if market_filter else None

    monitor = None
    end_timestamp = None
    
    showTitle("Mempool monitor", "bold yellow")

    console.log("Initializing...")
    console.log(f"Monitoring trades from: {wallet}")
    console.log(f"wallet balance: ${getBalance(wallet):,.2f}")
    console.log(f"positions value: ${getAllPositionsValue(wallet):,.2f}")
    console.log(f"Expected runtime: {runtime} seconds")

    if is_activated:
        console.log("[bold red] !!!WARNING!!!")
        console.log("[bold red] Copy trading is activated. Real money will be used [/]")
        console.log(f"Your wallet balance: ${getBalance(MY_WALLET):,.2f}")
    else:
        console.log(f"[bold yellow]Copy trading is not activated[/]")
    
    print()
    message_count = 0

    start_timestamp = int(time.time())
    if start_time:
        start_timestamp = get_start_timestamp(start_time)
        if start_timestamp < time.time():
            raise ValueError("Invalid starting time! Adjust or deactivate scheduled start")
        console.log("Scheduled start at: " + start_time)

    slugs = load_market_slugs(start_timestamp, start_timestamp + runtime)
    idMap = getIdMap(slugs)
    console.log("[bold green]Fetched market id map [/]")

    filter_ids = filter_target_ids(idMap, filters) if filters else None
    if filters: console.log("[bold green]Filter is active[/]")
    else: console.log("[bold yellow]Filter is not active[/]")
    
    client = await init_client()
    monitor = MempoolMonitor(wallet, idMap, filter_ids, client, is_activated)

    while start_timestamp > time.time():
        time.sleep(0.1)
    try:
        async with connect(WSS_URL) as websocket:
            pending_subscription = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "alchemy_pendingTransactions", 
                    { "toAddress": CTF_EXCHANGE }
                ]
            }
            
            await websocket.send(orjson.dumps(pending_subscription))
            await websocket.recv()
            console.log(f"Subscribed to PENDING transactions (mempool)")
    
            #console.log(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
            console.log("LIVE - Waiting for trades...")
            print("")
            
            running = True
            #trades: List[Trade] = []
            while running:
                message = await websocket.recv()
                message_count += 1
                
                # Print every 1000th message to show we're getting data
                if message_count == 100 or message_count % 1000 == 0:
                    print(f"Received {message_count} messages...")
                
                data = orjson.loads(message)

                if "params" in data and "result" in data["params"]:
                    result = data["params"]["result"]
                    
                    # Check if it's a pending transaction (from mempool)
                    if "hash" in result and "from" in result and "input" in result:
                        # This is a full transaction object (pending)
                        # print("mempool", print(result))
                        # print("mempool")
                        await monitor.process_pending_transaction(result)
    
                # stop condition
                if time.time() - start_timestamp >= runtime: #or len(trades) >= 50:
                    running = False
                    end_timestamp = start_timestamp  + runtime
    finally:
        shutdown(monitor, start_timestamp, end_timestamp, market_filter, is_save_logs)
        

if __name__ == "__main__":
    try:
        asyncio.run(monitor_trades())
    except KeyboardInterrupt:
        sys.exit()
    