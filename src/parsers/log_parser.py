from dotenv import load_dotenv
import os
from web3 import Web3

from pprint import pprint
from dataclasses import dataclass
from typing import List, Literal
from json import load

from src.parsers.hex_parser import Transaction

logTypeMap = {
    "d543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee": "OrderFilled",
    "c3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62": "TransferSingle",
    "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer",
    "8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925": "Approval",
    "b608d2bf25d8b4b744ba23ce2ea9802ea955e216c064a62f42152fbf98958d24": "FeeCharged",
    "b608d2bf25d8b4b744ba23ce2ea9802ea955e216c064a62f42152fbf98958d24": "FeeRefunded",
    "174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c": "OrdersMatched"
}

load_dotenv()
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
URL = f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"


@dataclass
class Log:
    address: str
    logIndex: int
    eventType: str
    topics: List[str]
    data: str
    
type Logs = list[Log]

class OrderFilledTopics:
    def __init__(self, topics: list):
        self.orderHash = topics[1]
        self.maker = topics[2]
        self.taker = topics[3]

class OrderFilledData:
    def __init__(self, data: str):
        values = []
        for i in range(len(data) // 64):
            values.append(data[i * 64:(i+1)*64])

        self.makerAssetId = values[0]
        self.takerAssetId = values[1]
        self.makerAmountFilled = values[2]
        self.takerAmountFilled = values[3]
        self.fee = values[4]

class TransferSingleEvent:
    def __init__(self, data: str):
        self.id = data[:64]
        self.value = data[64:]

class FeeRefundedEvent:
    def __init__(self, data: str):
        self.id = data[0:64]
        self.refund = data[64:]

def _filterLogs(logs: list[dict], target: str) -> list[dict]:
    filtered_logs: list[dict] = []
    for log in logs:
        if any({str(address.hex()) == target for address in log["topics"][0:4]}):
            filtered_logs.append(log)
    return filtered_logs

def _parseLogs(logs: list[dict]) -> Logs:
    parsed_logs: Logs = []
    important_keys = ["address", "logIndex", "eventType", "topics", "data"]
    for log in logs:
        values = {}
        for key in log:
            val = log[key]
            if key == "data":
                values[key] = str(val.hex())
            elif key == "topics":
                event = str(val[0].hex())
                if event not in logTypeMap:
                    values["eventType"] = "Unknown"
                else:
                    values["eventType"] = logTypeMap[event]
                values[key] = [str(elem.hex()) for elem in val]
            elif key in important_keys:
                values[key] = val
        parsed_logs.append(Log(**values)) 
    return parsed_logs


def analyze_logs(logs, wallet) -> Transaction:
    wallet_padded = f"000000000000000000000000{wallet[2:]}"
    PADDING = 1_000_000
    logs = _parseLogs(_filterLogs(logs, wallet_padded)) # type: ignore

    usdc_amount = 0
    shares = 0
    fee = 0
    token_id = "0x"
    for log in logs:
        if log.eventType == "OrderFilled":
            topics = OrderFilledTopics(log.topics)
            if topics.maker != wallet_padded:
                continue
            order = OrderFilledData(log.data)
            token_id = "0x" + order.takerAssetId
            usdc_amount = int(order.makerAmountFilled, 16) / PADDING
            shares = int(order.takerAmountFilled, 16) / PADDING
            fee = int(order.fee, 16) / PADDING

    return Transaction(wallet, token_id, shares, usdc_amount, fee, "BUY", 0)

def get_receipt(tx_hash):
    w3 = Web3(Web3.HTTPProvider(URL, request_kwargs={"timeout": 30}))
    receipt = w3.eth.get_transaction_receipt(tx_hash) 
    return receipt

def get_logs(tx_hash):
    receipt = get_receipt(tx_hash)
    return receipt.logs

def main():
    from src.tests.manage_hex_data import get_hex_data
    from src.parsers.hex_parser import parse_calldata
    from src.tests.get_transactions import get_tx_hashes
    from rich import print

    wallet = "0x13e0d447520ebe7f8eeaf7817211201b2c585204".lower()
    """
    tx_hashes = [
    '0xe34f99a4dd8ca74a9d4ea9b5ec4d3532a68d6d72fc5ddf1acb00997a9403f49d',
    '0xc07b4bb09aaf8f2d7a5590faf82e7baad9b61dbbdaeeb98073297c0109eafe5d',
    '0x78a19e6b2cb267fdccd54fd6935ba816d85ac9eb9f186b29aa0da79baf81e181',
    '0x47184a5c18aacc42a7c0b3bea91f5e2506496daea14dc9c0b0fc0d28c4673646',
    '0x5b3618fb8e16f13bb9374a6ad4f22823f32f714df01fecb310528c9c376b9323',
    '0xb66e0e4cbf51fe71ed2914227b6c771ebed5f043a951bcee5069014494a680a4',
    '0xbcfe3056d9b2611e1c17dfdbfaa6412be74d9569f91cf21b571811d56ab13923',
    '0xcc29bf5f3b98ff824877b9417c76ecb005f27772df040f7df942a8c0d5da6bac',
    '0x3f0ad83b2f55e6d663599e3b5688ad0afa69c88dbb6398cde8b9ee8cd8d69e51',
    '0x066cc19aef46fd38377eac338debe5f62fc22027e065c18f75b1b591cb6ec798'
]
    """
    tx_hashes = get_tx_hashes(wallet, 10)
    print(tx_hashes)
    passes = 0
    for tx_hash in tx_hashes:
        print(tx_hash)
        tx = parse_calldata(get_hex_data(tx_hash), wallet)
        print(tx)

        log_tx = analyze_logs(get_logs(tx_hash), wallet)
        print(log_tx)
        if log_tx == tx:
            passes += 1
        print("=====" * 5)
    print(len(tx_hashes), passes)

if __name__ == "__main__":
    main()