from src.marketIdMapper import getMarketBySlug, load_market_slugs, get_historic_id_map
from src.types import marketOutcome, Transaction, Transactions, init_trade, Trades, Positions, Side, MarketSummary
from src.analytics.positionSummary import calcPositions
from src.tests.get_transactions import get_tx_hashes
from src.tests.manage_hex_data import get_hex_data
from src.parsers.hex_parser import parse_calldata
from polymarket import Market
from rich.console import Console
import time

console = Console()

def _is_market_open(market: Market, timestamp = time.time()) -> bool:
    end_timestamp = market.state.end_date.timestamp()
    return end_timestamp > timestamp

def get_market_outcome(slug) -> marketOutcome | None:
    market = getMarketBySlug(slug)
    if _is_market_open(market):
        return None

    upPrice = float(str(market.outcomes.yes.price))
    downPrice = float(str(market.outcomes.no.price))

    return  "up" if upPrice > downPrice else "down"

def get_tx(wallet: str, tx_hash: str) -> Transaction | None:
    hex_data = get_hex_data(tx_hash)
    return parse_calldata(hex_data, wallet)

def get_txs(wallet: str, timestamp: int, duration: int):
    with console.status("[bold green] Fetching tx hashes..."):
        tx_hashes = get_tx_hashes(wallet, start_timestamp=timestamp, end_timestamp=timestamp + duration)
    txs = {}
    with console.status(f"[bold green] Fetching {len(tx_hashes)} transactions..."):
        for tx_hash in tx_hashes:
            console.log(f"[bold blue] Fetching {tx_hash}")
            tx = get_tx(wallet, tx_hash)
            if tx is not None:
                txs[tx_hash] = tx
    return txs 

def get_trades(wallet: str, timestamp: int, duration: int) -> Trades:
    with console.status("[bold green] Constructing id map..."):
        slugs = load_market_slugs(timestamp, timestamp + duration)
        idMap = get_historic_id_map(slugs)

    txs = get_txs(wallet, timestamp, duration)
    trades = {}
    for tx_hash, tx in txs.items():
        trade = init_trade(tx_hash, tx, idMap)
        trades[tx_hash] = trade
    return trades

def get_positions(wallet: str, timestamp: int, duration: int) -> Positions:
    trades = get_trades(wallet, timestamp, duration)
    positions = calcPositions(trades)
    return positions

def calcMarkets(positions: Positions):

    market_outcomes = {}
    for pos in positions.values():
        if pos.conditionId not in market_outcomes:
            market_outcomes[pos.conditionId] = get_market_outcome(pos.slug)
    
    markets = []
    for conditionId, outcome in market_outcomes:
        downPos, upPos = None, None
        for pos in positions.values():
            if pos.conditionId == conditionId:
                if pos.side == "up":
                    upPos = pos
                else:
                    downPos = pos
        market = MarketSummary(upPos, downPos, outcome)
        markets.append(market)



if __name__ == "__main__":
    timestamp = 1783516500
    wallet = "0xce25e214d5cfe4f459cf67f08df581885aae7fdc"
    get_positions(wallet, timestamp, 300)