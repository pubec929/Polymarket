import os

from rich.console import Console

from src.analytics.menu import selectFileMenu, selectActionMenu

from src.analytics.positionSummary import showPositions
from src.analytics.getMissedTxs import getMissedTxs
from src.analytics.marketSummary import showMarkets
from src.types import list_metadata_files, BASE_PATH_METADATA

console = Console()


def selectFile():
    files = list_metadata_files()
    file_name = selectFileMenu(files)
    file_path = f"{BASE_PATH_METADATA}/{file_name}"
    return file_path

def selectAction(actions):
    action = selectActionMenu(list(actions.keys()))
    return actions[action]

def run():
    actions = {
        "position summary": showPositions,
        "show missed transactions": getMissedTxs,
        "market summary": showMarkets
    }

    session_file = selectFile()
    func = selectAction(actions)
    print(session_file)
    print("\n\n")
    func(session_file)

if __name__ == "__main__":
    run()