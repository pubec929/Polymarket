from src.marketIdMapper import getMarketBySlug, load_market_slugs, get_historic_id_map
from src.types import marketOutcome, Transaction, Transactions, init_trade, Trades, Positions, Side, Market, Markets, save_trades, load_trades
from src.analytics.positionSummary import calcPositions
from src.tests.get_transactions import get_tx_hashes
from src.tests.manage_hex_data import get_hex_data
from src.parsers.hex_parser import parse_calldata
from polymarket import Market as PolyMarket
from rich.console import Console
import time

console = Console()

def _is_market_open(market: PolyMarket, timestamp = time.time()) -> bool:
    end_timestamp = market.state.end_date.timestamp()
    return end_timestamp > timestamp

def get_market_outcome(slug: str) -> marketOutcome | None:
    if slug == "Unknown Market":
        return None
    market = getMarketBySlug(slug)
    if _is_market_open(market):
        return None

    upPrice = float(str(market.outcomes.yes.price))
    downPrice = float(str(market.outcomes.no.price))

    return  "up" if upPrice > downPrice else "down"

if __name__ == "__main__":
    """
    from rich import print
    timestamp = 1783691400
    timespans = 10
    wallet = "0xf3531b23b504cf0aed4ff21325232b2a2d496685"
    #positions = get_positions(wallet, timestamp, 300)
    #for pos in positions.values():
    #    pos.display()
    positions = {}
    for i in range(timespans):
        positions = positions | get_positions(wallet, timestamp + i * 300, 300)
    #positions = get_positions(wallet, timestamp, 300)
    markets = calcMarkets(positions)
    display(markets)
    #slug = "btc-updown-5m-1783688400"
    #print(get_market_outcome(slug))
    """