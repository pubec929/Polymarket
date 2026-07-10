from datetime import datetime
from pytz import timezone
import json
import os
import time
from polymarket import PublicClient, Market
from typing import Literal

from src.types import MarketData, IdMap

BASE_PATH = "./data/market_id_maps"

def getLastTimestamp(minutes: Literal[5, 15, 60], timestamp = int(time.time())):
    seconds = minutes * 60
    return timestamp // seconds * seconds

def preload_timestamps(start_time: int, end_time: int, minutes: Literal[5, 15, 60]) -> list[int]:
    seconds = minutes * 60
    start_time = start_time // seconds * seconds
    return [timestamp for timestamp in range(start_time, end_time, seconds)]

def getMarketSlugs(minutes: Literal[5, 15, 60], timestamp: int):
    if timestamp % (minutes * 60) != 0:
        raise ValueError
    if minutes != 60:
        base_slugs = ["btc-updown", "eth-updown", "sol-updown", "xrp-updown"]
        return [f"{slug}-{minutes}m-{timestamp}" for slug in base_slugs]
    else:
        base_slugs = ["bitcoin-up-or-down-", "ethereum-up-or-down-", "solana-up-or-down-", "xrp-up-or-down-"]
        tz = timezone("US/Eastern")
        date = datetime.fromtimestamp(timestamp, tz)
        date = date.strftime("%B-%d-%Y-%I%p").lower().replace("-0", "-") + "-et"
        return [slug + date for slug in base_slugs]

def load_market_slugs(start_time: int, end_time: int):
    market_minutes: list[Literal[5, 15, 60]] = [5, 15, 60]
    market_slugs = []
    for minute in market_minutes:
        timestamps = preload_timestamps(start_time, end_time, minute)
        for timestamp in timestamps:
            market_slugs.extend(getMarketSlugs(minute, timestamp))

    return market_slugs

def saveIdMap(id_map: IdMap, timestamp: int) -> str:        
    file_path = getFilePath(timestamp)
    id_map_json = {token_id: market.toJSON() for token_id, market in sorted(id_map.items(), key=lambda val: val[1].question)}
    with open(file_path, "w") as file:
        json.dump(id_map_json, file, indent=4)
    return file_path

def openIdMap(timestamp: int) -> IdMap:
    file_path = getFilePath(timestamp)
    if not os.path.exists(file_path):
        raise ValueError
    
    with open(file_path, "r") as file:
        json_data = json.load(file)

    return {key: MarketData(**json.loads(val)) for key, val in json_data.items()}
    
def getFilePath(timestamp: int):
    return f"{BASE_PATH}/marketIdMap-{timestamp}.json"

def getMarketsBySlug(slugs: list[str]) -> list[Market]:
    client = PublicClient()

    markets = client.list_markets(slug=slugs)
    return [market for page in markets for market in page.items]

def getIdMap(slugs: list[str]):
    def _zero_pad(string: str, length: int):
        while len(string) < length:
            string = "0" + string 
        return string
    
    def _convert_token_id(raw_token_id):
        token_id = hex(int(raw_token_id))
        return "0x" + _zero_pad(token_id[2:], 64)
    
    markets = getMarketsBySlug(slugs)
    id_map: dict[str, MarketData] = {}
    for market in markets:
        token_id_up = _convert_token_id(market.outcomes.yes.token_id)
        token_id_down = _convert_token_id(market.outcomes.no.token_id)
        clobTokenIds = (token_id_up, token_id_down) # type: ignore
        data = (market.id, market.question, market.slug, market.condition_id, clobTokenIds)
        id_map[clobTokenIds[0]] = MarketData(*data, "up") # type: ignore
        id_map[clobTokenIds[1]] = MarketData(*data, "down") # type: ignore

    return id_map

def getMarketBySlug(slug) -> Market:
    client = PublicClient()
    market = client.get_market(slug=slug)
    return market

def get_historic_id_map(slugs: list[str]):
    def _zero_pad(string: str, length: int):
        while len(string) < length:
            string = "0" + string 
        return string
    
    def _convert_token_id(raw_token_id):
        token_id = hex(int(raw_token_id))
        return "0x" + _zero_pad(token_id[2:], 64)
    
    markets = [getMarketBySlug(slug) for slug in slugs]
    id_map: dict[str, MarketData] = {}
    for market in markets:
        token_id_up = _convert_token_id(market.outcomes.yes.token_id)
        token_id_down = _convert_token_id(market.outcomes.no.token_id)
        clobTokenIds = (token_id_up, token_id_down) # type: ignore
        data = (market.id, market.question, market.slug, market.condition_id, clobTokenIds)
        id_map[clobTokenIds[0]] = MarketData(*data, "up") # type: ignore
        id_map[clobTokenIds[1]] = MarketData(*data, "down") # type: ignore

    return id_map
