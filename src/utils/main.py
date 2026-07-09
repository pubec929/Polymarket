import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
from web3 import Web3

load_dotenv()
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY") or ""
RPC_URL = os.getenv("RPC_URL") or ""

PUSD_CONTRACT = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"

def getBalance(wallet: str) -> float:
    web3 = Web3(Web3.HTTPProvider(RPC_URL))

    pusd = web3.eth.contract(
        address=Web3.to_checksum_address(PUSD_CONTRACT),
        abi=[{
            "name": "balanceOf",
            "inputs": [{"name": "owner", "type": "address"}],
            "outputs": [{"type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }]
    )

    balance = pusd.functions.balanceOf(Web3.to_checksum_address(wallet)).call() / 1e6
    return balance

def getAllPositionsValue(wallet):
    url = "https://data-api.polymarket.com/positions"
    params = {
        "user": wallet,
        "limit": 500
    }
    response = requests.get(url, params).json()
    total_amount = 0
    for position in response:
        total_amount += position["currentValue"]
    return total_amount

def get_start_timestamp(start_time: str) -> int:
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day

    return int(datetime.strptime(f"{day}/{month}/{year} {start_time}", "%d/%m/%Y  %H:%M:%S").timestamp())

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_property(collection, property: str):
    properties = []
    for item in collection:
        properties.append(getattr(item, property))
    return properties


def get_timestamp_from_slug(slug: str):
    months = { "january": 1,  "february": 2, "march": 3, "april": 4, 
               "may": 5, "june": 6, "july": 7, "august": 8, 
               "september": 9, "october": 10, "november": 11, "december": 12}

    if "5m" in slug or "15m" in slug:
        *_, timestamp = slug.split("-")
        return int(timestamp)
    elif "pm" in slug or "am" in slug:
        year = datetime.now().year
        *_, month, day, hour, tz = slug.split("-")

        hour = int(hour[:-2]) if hour[-2:] == "am" else (int(hour[:-2]) + 12) % 24
        #print(hour)
        date = datetime.strptime(f"{day}/{months.get(month)}/{year} {hour}:00:00", "%d/%m/%Y %H:%M:%S")

        eastern = pytz.timezone("US/Eastern")
        date_eastern = eastern.localize(date)  # attach ET timezone
        date_utc = date_eastern.astimezone(pytz.utc)  # convert to UTC

        return int(date_utc.timestamp())