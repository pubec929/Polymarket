from src.types import Position, Positions, Trades, display
from src.types import load_metadata, load_trades
from src.analytics.getTrades import _fetch_trades

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


def _load_positions(path) -> Positions:
    trades = load_trades(path)
    return calcPositions(trades)

def _fetch_positions(wallet: str, timestamp: int, duration: int) -> Positions:
    trades = _fetch_trades(wallet, timestamp, duration)
    return calcPositions(trades)

def get_positions():    
    ...
def showPositions(file_path):
    metadata = load_metadata(file_path)
    positions = _load_positions(metadata.session_logs_path)
    display(positions)

if __name__ == "__main__":
    positions = _fetch_positions("0xce25e214d5cfe4f459cf67f08df581885aae7fdc", 1783723500, 300)
    display(positions)