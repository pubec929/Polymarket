from src.analytics.positionSummary import showPositionsFromPast
from src.analytics.marketSummary import showMarketsFromPast
from src.analytics.menu import selectMenu, showTitle
from src.analytics.candidates import selectWallet
from src.marketIdMapper import getLastTimestamp

import questionary

def selectAction():
    actions = {
        "Show past markets": showMarketsFromPast,
        "Show past positions": showPositionsFromPast
    }

    return selectMenu("Select an action...", actions)
  
def validateInt(min_num: int | None = None, max_num: int | None = None):
    def _validateInt(string: str):
        if not string:
            return "input must not be empty"
        
        if not string.isdigit():
            return "input must consist of only valid digits"
        
        num = int(string)
        if min_num and max_num:
            if num < min_num:
                return "input is too small"
            if num > max_num:
                return "input is too big"

        return True
    return _validateInt

def validTimestamp(min_num: int, max_num: int):
    def _valideTimestamp(string: str):
        validate = validateInt(min_num, max_num)
        err = validate(string)
        if type(err) == str:
            return err
        num = int(string)
        if num % 300 != 0:
            return "invalid timestamp"
        return True

    return _valideTimestamp

def validateDuration(min_num: int, max_num: int):
    def _validateDuration(string: str):
        validate = validateInt(min_num, max_num)
        err = validate(string)
        if type(err) == str:
            return err
        num = int(string)
        if num %  300 != 0:
            return "invalid duration"
        return True

    return _validateDuration

def selectTimestamp():
    min_timestamp = 1767225600 # 12am 1. January 2026
    max_timestamp = getLastTimestamp(5) - 300
    return int(questionary.text("Enter the start timestamp: ", validate=validTimestamp(min_timestamp, max_timestamp)).ask())

def selectDuration(start_timestamp: int):
    min_duration = 300
    max_duration = getLastTimestamp(5) - start_timestamp
    return int(questionary.text("Enter the duration: ", validate=validateDuration(min_duration, max_duration), default=str(300)).ask())

def selectTimespan():
    options = [
        "specific time range",
        "most recent markets"
    ]
    selected_option = selectMenu("Analyse...", options)
    if selected_option == "specific time range":
        timestamp = selectTimestamp()
        duration = selectDuration(timestamp)
    else:
        default_num = 10
        num_markets = int(questionary.text("Enter number of markets: ", validate=validateInt(1, 30), default=str(default_num)).ask())
        end_timestamp = getLastTimestamp(5)
        duration = num_markets * 300
        timestamp = end_timestamp - duration
    return timestamp, duration


def run():
    showTitle("Wallet Analysis", "bold yellow")
    func = selectAction()
    wallet = selectWallet()
    timestamp, duration = selectTimespan()
    func(wallet, timestamp, duration)
    

if __name__ == "__main__":
    run()
