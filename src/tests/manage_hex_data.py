import requests
import os
from dotenv import load_dotenv
import time
from rich.console import Console

load_dotenv()
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY") or ""

FILE_PATH = "./data/test-data/hex_data/"
METHOD_ID = "0x3c2b4399"

console = Console()

def _fetch_hex_data(tx_hash: str) -> str | None:
    """requests the raw hex data from the alchemy api"""
    url = f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getTransactionByHash",
        "params": [tx_hash]
    }
    headers = {"Content-Type": "application/json", "apiKey": f"{ALCHEMY_API_KEY}"}
    response = requests.post(url, json=payload, headers=headers).json()
    
    if "result" in response:
        return response["result"]["input"]

    return None

def _fetch_hex_data_with_retries(tx_hash: str, retries: int = 10, debug: bool = False) -> str | None:
    for _ in range(retries):
        hex_data = _fetch_hex_data(tx_hash)
        if hex_data:
            return hex_data
        if debug:
            console.log(f"[bold red] Failed to fetch hex data! Retrying...")
        time.sleep(1)
    return None
    
def _save_to_file(file_path: str, contents: str) -> bool:
    """intended to save raw hex data to disk for later use"""
    with open(file_path, "w") as file:
        file.write(contents)
    return True


def get_chunks(hex_data: str, method_id = "0x3c2b4399", chunk_size = 64) -> list[str]:
    """splits up the raw hex data into chunks of the same size"""
    hex_data = hex_data[len(method_id):]
    return [hex_data[i*chunk_size:(i+1)*chunk_size] for i in range(len(hex_data) // chunk_size)]

def _read_from_file(file_path: str):
    """intended to read raw transaction hex data from file"""
    if not os.path.exists(file_path):
        raise ValueError("file does not exist: ", file_path)
    
    with open(file_path, "r") as file:
        calldata = file.read()
    return calldata

def save_hex_data(tx_hash: str, hex_data: str | None = None) -> bool:
    """fetches the hex data from the alchemy api and directly saves it to disk"""
    if not hex_data:
        hex_data = _fetch_hex_data_with_retries(tx_hash)
    if hex_data and hex_data[:len(METHOD_ID)] == METHOD_ID:
        return _save_to_file(f"{FILE_PATH}{tx_hash}.txt", hex_data)
    return False

def get_hex_data(tx_hash: str):
    """Gets the transaction hex data for the requested tx_hash. if a file exists the data is read from it otherwise the api is called"""
    file_path = f"{FILE_PATH}{tx_hash}.txt"

    if os.path.exists(file_path): 
        return _read_from_file(file_path)
    else:
        return _fetch_hex_data_with_retries(tx_hash)
