from src.types import Position, Positions, Trades
from src.types import load_metadata, load_trades

def sort_dict(dictionary: dict):
    keys = sorted(dictionary.keys())
    return {k: dictionary[k] for k in keys}

def calcPositions(trades: Trades):
        positions: Positions = {}
        for trade in trades.values():
            if trade.tokenId not in positions:
                positions[trade.tokenId] = Position(trade.tokenId, trade.conditionId, trade.market_name, trade.slug, trade.wallet, trade.side, 0, 0, 0)

            position = positions[trade.tokenId]
            position.total_trades += 1
            if trade.action == "BUY":
                position.shares += trade.shares
                position.usdc_amount += trade.usdc_amount

            elif trade.action == "SELL":
                position.shares -= trade.shares
                position.usdc_amount -= trade.usdc_amount
    
        return positions

def positionSummary(file_path):
    metadata = load_metadata(file_path)
    trades = load_trades(metadata.session_logs_path) 
    positions = calcPositions(trades)

    positions = sort_dict(positions)
    for pos in positions.values():
        pos.display()
