from polymarket import Market as PolyMarket
import time

from src.types import marketOutcome
from src.marketIdMapper import getMarketBySlug


def _is_market_open(market: PolyMarket, timestamp = time.time()) -> bool:
    end_timestamp = market.state.end_date.timestamp()
    return end_timestamp > timestamp

def get_market_outcome(slug: str) -> marketOutcome | None:
    if slug == "Unknown Market":
        return None
    market = getMarketBySlug(slug)
    if _is_market_open(market):
        return None

    upPrice = float(str(market.outcomes.yes.price))
    downPrice = float(str(market.outcomes.no.price))

    return  "up" if upPrice > downPrice else "down"