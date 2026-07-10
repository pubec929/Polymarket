from src.types import Transaction, Trades, init_trade, load_trades
from src.parsers.hex_parser import parse_calldata
from src.tests.manage_hex_data import get_hex_data
from rich.console import Console
from src.tests.get_transactions import get_tx_hashes
from src.marketIdMapper import load_market_slugs, get_historic_id_map

console = Console()

def fetch_tx(wallet: str, tx_hash: str) -> Transaction | None:
    hex_data = get_hex_data(tx_hash)
    return parse_calldata(hex_data, wallet)

def fetch_txs(wallet: str, timestamp: int, duration: int):
    with console.status("[bold green] Fetching tx hashes..."):
        tx_hashes = get_tx_hashes(wallet, start_timestamp=timestamp, end_timestamp=timestamp + duration)
    txs = {}
    with console.status(f"[bold green] Fetching {len(tx_hashes)} transactions..."):
        for tx_hash in tx_hashes:
            console.log(f"[bold blue] Fetching {tx_hash}")
            tx = fetch_tx(wallet, tx_hash)
            if tx is not None:
                txs[tx_hash] = tx
    return txs 

def _fetch_trades(wallet: str, timestamp: int, duration: int) -> Trades:
    with console.status("[bold green] Constructing id map..."):
        slugs = load_market_slugs(timestamp, timestamp + duration)
        idMap = get_historic_id_map(slugs)

    txs = fetch_txs(wallet, timestamp, duration)
    trades = {}
    for tx_hash, tx in txs.items():
        trade = init_trade(tx_hash, tx, idMap)
        trades[tx_hash] = trade
    return trades


def get_trades(path: str | None = None, wallet: str | None = None, timestamp: int | None = None, duration: int | None = None) -> Trades | None:
    if path:
        return load_trades(path)
    
    if wallet and timestamp and duration:
        return _fetch_trades(wallet, timestamp, duration)
    return None