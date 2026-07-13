from src.utils.jsonHelper import loadJSON
from src.analytics.menu import selectMenu

from dataclasses import dataclass

FILE_PATH = "data/candidates.json"

@dataclass
class Candidate:
    name: str
    address: str

type Candidates = list[Candidate]

def load_candidates() -> Candidates:
    json_data = loadJSON(FILE_PATH)
    return [Candidate(**obj) for obj in json_data]

def selectWallet() -> str:
    candidates = load_candidates()
    # convert candidates to options
    options = {candidate.name: candidate.address for candidate in candidates}
    wallet = selectMenu("Select a wallet...", options)
    return wallet

if __name__ == "__main__":
    from rich import print
    print(selectWallet())