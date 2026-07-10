
class ColorMap:
    RED = "#FF0000"          
    GREEN = "#00FF00"       
    ORANGE = "#FFAF00"       
    BUY = "#3A96DD"          
    SELL = "#B4009E"         

class MarketColorMap:
    ethereum = "#005FFF"     
    bitcoin = "#FFAF00"      
    solana = "#9B51F7"       
    xrp = "#0087FF"   
    default = ""       

def getMarketColor(market_name: str):
    market_name = market_name.lower()
    for market in MarketColorMap.__dict__:
        if market in market_name:
            return getattr(MarketColorMap, market)

    return ""