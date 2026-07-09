from src.types import IdMap

def verfiy_filters(filters: list[str]) -> bool:
    market_names = set(["btc", "eth", "sol", "xrp", "*"])
    minutes = set(["5min", "15min", "60min", "*"])

    for filter in filters:
        if "/" not in filter:
            return False
        name, minute = filter.split("/")
        if name not in market_names or minute not in minutes:
            return False
    return True

def parse_filters(market_filter: str) -> list[tuple[str, str]]:
    if ";" in market_filter:
        market_filters = [*market_filter.split(";")]
    else:
        market_filters = [market_filter]

    if not verfiy_filters(market_filters):
        raise ValueError("Invalid filter parameters", market_filters)
    
    name_map = {
        "btc": "Bitcoin",
        "eth": "Ethereum",
        "sol": "Solana",
        "xrp": "XRP"
    }

    filters: list[tuple[str, str]] = []
    for m_filter in market_filters:
        name, minute = m_filter.split("/")
        if minute != "*":
            if minute == "60min":
                minute = "-et"
            else:
                minute = "-" + minute.removesuffix("in") + "-"
        if name != "*":
            name = name_map[name]
        filters.append((name, minute))

    return filters

def filter_target_ids(id_map: IdMap, filters: list[tuple[str, str]]) -> set[str]:
    filtered_id_map: IdMap = {}

    for token_id, market in id_map.items():
        for name, minute in filters:
            if name == "*" or name in market.question:
                if minute == "*" or minute in market.slug:
                    filtered_id_map[token_id] = market
                    break

    return set([token_id for token_id in filtered_id_map])