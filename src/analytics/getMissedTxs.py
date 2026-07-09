from src.tests.get_transactions import get_tx_hashes
from src.tests.manage_hex_data import get_hex_data
from src.parsers.hex_parser import parse_calldata
from src.types import init_trade, load_metadata, load_trades
from src.marketIdMapper import openIdMap

from rich.console import Console

console = Console()

def getMissedTxs(file_path: str):
    metadata = load_metadata(file_path)
    trades = load_trades(metadata.session_logs_path)
    
    with console.status("[bold gree] Fetching tx hashes ...", spinner="dots"):
        tx_hashes = set(get_tx_hashes(metadata.wallet, start_timestamp=metadata.start_time, end_timestamp=metadata.end_time))

    recorded_tx_hashes = set(trades.keys())
    missed_tx_hashes = tx_hashes - recorded_tx_hashes
    markets = openIdMap(metadata.start_time)
    for tx_hash in missed_tx_hashes:
        hex_data = get_hex_data(tx_hash)
        transaction = parse_calldata(hex_data, metadata.wallet)
        if transaction:
            trade = init_trade(tx_hash, transaction, markets)
            trade.display(verbose=True)

    console.print("\n[bold cyan] missed transaction hashes: [/]")
    console.print(missed_tx_hashes)
    console.print(f"[bold cyan] Total missed: {len(missed_tx_hashes)}")
