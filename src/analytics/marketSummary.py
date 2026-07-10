from src.types import load_metadata, load_trades, Positions, Markets, Market, Position, display

from src.analytics.historic_trade_data import get_market_outcome
from src.analytics.positionSummary import _load_positions, _fetch_positions
from rich import print

def calcMarkets(positions: Positions) -> Markets:

    market_outcomes = {}
    for pos in positions.values():
        if pos.conditionId not in market_outcomes:
            outcome = get_market_outcome(pos.slug)
            if outcome is not None:
                market_outcomes[pos.conditionId] = outcome
    
    markets: Markets = {}
    for conditionId, outcome in market_outcomes.items():
        downPos, upPos = None, None
        for pos in positions.values():
            if pos.conditionId == conditionId:
                if pos.side == "up":
                    upPos = pos
                else:
                    downPos = pos
        if downPos is None and upPos is None:
            continue
        market = Market(upPos, downPos, outcome)
        markets[conditionId] = market
    return markets

def _load_markets(path) -> Markets:
    positions = _load_positions(path)
    return calcMarkets(positions)

def _fetch_markets(wallet: str, timestamp: int, duration: int) -> Markets:
    positions = _fetch_positions(wallet, timestamp, duration)
    return calcMarkets(positions)

def showMarkets(path):
    metadata = load_metadata(path)
    markets = _load_markets(metadata.session_logs_path)
    display(markets)