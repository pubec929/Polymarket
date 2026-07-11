import requests
import os
from dotenv import load_dotenv
from typing import Literal
load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY") or ""
URL = "https://api.etherscan.io/v2/api"

METHOD_ID = "0x3c2b4399"

def get_tx_hashes(wallet: str, start_timestamp: int | None = None, end_timestamp: int | None = None, num: int | None = None) -> list[str]:
    """returns a list of all the tx_hashes of transactions in a given time period"""
    tx_logs = get_tx_logs(wallet, start_timestamp, end_timestamp, num)
    return [tx_log["hash"] for tx_log in tx_logs]

def get_tx_logs(wallet: str, start_timestamp: int | None = None, end_timestamp: int | None = None, num: int | None = None) -> list[dict]:
    """
    https://docs.etherscan.io/api-reference/endpoint/tokentx
    returns the transaction logs of the n-most recent transactions of the specified wallet
    """
    def _is_tx_log_valid(tx_log: dict):
        return tx_log["methodId"] == METHOD_ID

    params = {
        "apikey": ETHERSCAN_API_KEY,
        "chainid": 137,
        "module": "account",
        "action": "tokentx",
        "contractaddress": "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB",
        "address": wallet,
        "sort": "desc"
    }

    if start_timestamp:
        start_block = get_block_number_by_timestamp(start_timestamp, "before")
        params["startblock"] = start_block
    
    if end_timestamp:
        end_block = get_block_number_by_timestamp(end_timestamp, "after")
        params["endblock"] = end_block

    response = requests.get(URL, params).json()
    tx_logs = response["result"]
    valid_tx_logs = [log for log in tx_logs if _is_tx_log_valid(log)]
    return valid_tx_logs[:num] if num else valid_tx_logs
    

def get_block_number_by_timestamp(timestamp: int, closest: Literal["before", "after"]):
    """
    https://docs.etherscan.io/api-reference/endpoint/getblocknobytime
    return the number of the block mined closest to the timestamp
    """
    params = {
        "apikey": ETHERSCAN_API_KEY,
        "chainid": 137,
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": timestamp,
        "closest": closest
    }
    response = requests.get(URL, params).json()
    result = response["result"]
    return int(result)
