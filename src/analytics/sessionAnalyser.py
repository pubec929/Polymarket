from rich.console import Console

from src.analytics.menu import selectMenu, showTitle

from src.analytics.positionSummary import showPositionsFromFile, showExpectedPositions
from src.analytics.getMissedTxs import getMissedTxs
from src.analytics.marketSummary import showMarketsFromFile, showExpectedMarktes
from src.types import list_metadata_files, BASE_PATH_METADATA

from datetime import datetime

console = Console()

def selectFile() -> str:
    files = list_metadata_files()
    options = {}
    for file_name in files:
        timestamp,_ = file_name.split("-")
        date = str(datetime.fromtimestamp(int(timestamp)))
        options[date] = file_name
    
    selected_file = selectMenu("Select a session...", options)
    file_path = f"{BASE_PATH_METADATA}/{selected_file}"
    return file_path

def selectAction():
    actions = {
        "show missed transactions": getMissedTxs,
        "show positions": showPositionsFromFile,
        "show markets": showMarketsFromFile,
        "show expected positions": showExpectedPositions,
        "show expected market": showExpectedMarktes
    }

    func = selectMenu("Select an action...", actions)
    return func

def run():
    showTitle("Session Analysis", "bold yellow")
    file_path = selectFile()
    func = selectAction()
    func(file_path)

if __name__ == "__main__":
    run()