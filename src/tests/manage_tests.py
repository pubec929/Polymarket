from src.types import Transaction
from src.utils.jsonHelper import saveAsJSON, loadJSON
from src.tests.manage_hex_data import get_hex_data, save_hex_data
from src.parsers.hex_parser import parse_calldata
from src.tests.get_transactions import get_tx_hashes

from rich.console import Console
from dataclasses import dataclass

console = Console()

FILE_PATH = "./data/test_data/test_cases.json"

@dataclass
class TestCase:
    tx_hash: str
    tx: Transaction

type TestCases = list[TestCase]

def add_test(tx_hash: str, wallet: str) -> bool:
    test_cases = load_test_cases()
    calldata = get_hex_data(tx_hash)
    tx = parse_calldata(calldata, wallet)
    if not tx or not calldata:
        return False
    test_cases.append(TestCase(tx_hash, tx))
    write_test_cases(test_cases)
    save_hex_data(tx_hash, calldata)
    return True
    

def add_tests(tx_hashes: list[str], wallet: str):
    added = 0
    with console.status("[bold green]Adding new test cases...[/]"):
        for i, tx_hash in enumerate(tx_hashes):
            console.log(f"Adding test case {tx_hash}")
            is_added = add_test(tx_hash, wallet)
            if is_added:
                added += 1
            else:
                console.log(f"[bold red] Error! Failed to add test case {tx_hash}[/]")
    console.log(f"Successfully added [bold green]{added}[/] test cases")
    
def load_test_cases() -> TestCases:
    json_data = loadJSON(FILE_PATH)
    test_cases = []
    for obj in json_data:
        tx = Transaction(**obj["tx"])
        test_cases.append(TestCase(obj["tx_hash"], tx))
    return test_cases

def write_test_cases(test_cases: TestCases): 
    saveAsJSON(test_cases, FILE_PATH)

def get_num_test_cases() -> int:
    return len(load_test_cases())

if __name__ == "__main__":

    from rich import print
    wallet = "0xce25e214d5cfe4f459cf67f08df581885aae7fdc"
    tx_hashes = get_tx_hashes(wallet, num=400)
    add_tests(tx_hashes, wallet)

