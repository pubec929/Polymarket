from src.types import load_metadata, load_trades

from src.analytics.historic_trade_data import get_market_outcome
from src.analytics.positionSummary import calcPositions
from rich import print

def marketSummary(file_path):
    metadata = load_metadata(file_path)
    trades = load_trades(metadata.session_logs_path)
    positions = calcPositions(trades)

    market_outcomes = {}
    for pos in positions.values():
        if pos.conditionId not in market_outcomes:
            market_outcomes[pos.conditionId] = get_market_outcome(pos.slug)
    
    print(market_outcomes)