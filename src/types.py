#from src.utils.main import Colors, cprint
from datetime import datetime
from dataclasses import dataclass
from typing import Literal
import json
import os

from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.console import Console

from src.utils.colors import getMarketColor, ColorMap
from src.utils.jsonHelper import saveAsJSON, loadJSON

console = Console()

type Side = Literal["up", "down", "unknown"]
type Action = Literal["BUY", "SELL"]
type marketOutcome = Literal["up", "down"] 

BASE_PATH_LOGS = "./data/session_logs"
BASE_PATH_METADATA = "./data/session_metadata"

@dataclass
class MarketData:
    id: str
    question: str
    slug: str
    conditionId: str
    clobTokenIds: tuple[str, str]
    side: Literal["up", "down"] 

    def toJSON(self):
        return json.dumps(self.__dict__)
    
@dataclass
class Transaction:
    wallet: str
    token_id: str
    shares: float
    usdc_amount: float
    fee: float
    action: Action
    timestamp: float

    def __eq__(self, other):
        if type(other) != Transaction:
            return False
        return self.wallet == other.wallet and self.token_id == self.token_id and self.usdc_amount == other.usdc_amount and self.fee == other.fee and self.action == other.action

@dataclass
class Trade:
    tx_hash: str # unique identifier
    tokenId: str
    conditionId: str
    wallet: str

    market_name: str
    slug: str
    side: Side
    action: Action

    usdc_amount: float
    fee: float
    shares: float
    price_per_share: float

    timestamp: float
    detection_time: float = 0.0

    def display(self, verbose=False):
        market_color = getMarketColor(self.market_name)
        side_color = ColorMap.GREEN if self.side == "up" else ColorMap.RED
        action_color = ColorMap.BUY if self.action == "BUY" else ColorMap.SELL
        
        params = [market_color, side_color, action_color]
        if verbose:
            self._display_verbose(*params)
        else:
            self._display_concise(*params)
        
    def _display_timestamp(self, timestamp: int | float):
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S")

    def _display_concise(self, market_color, side_color, action_color):
        console.print(f"\n{'='*20}> TRADE DETECTED <{'='*20}")
        console.print(f"Tx: {self.tx_hash}")
        console.print(f"${self.usdc_amount + self.fee:.2f} | [{action_color}]{self.action}[/]")
        console.print(f"[{market_color}]{self.market_name}[/] | [{side_color}]{self.side}[/]")
        console.print(f"Shares: {self.shares:.1f} | [{side_color}]{self.price_per_share * 100: .0f}¢[/]")
        #console.print(f"Timestamp: {datetime.fromtimestamp(self.timestamp)}")
        #console.print(f"Detection time: {datetime.fromtimestamp(self.detection_time)}")
        console.print(f"Delay: {self.detection_time - self.timestamp:.3f}s | Timestamp: {self._display_timestamp(self.timestamp)} | Detection time: {self._display_timestamp(self.detection_time)}")
        console.print("=" * 80)
        
    def _display_verbose(self, market_color, side_color, action_color):
        table = Table(
            show_header=False,
            box=box.SIMPLE_HEAVY,
            padding=(0, 2),
        )
        table.add_column("Field", style="bold", no_wrap=True)


        table.add_row(f"Tx: [blue]{self.tx_hash}[/]")
        table.add_row(f"[yellow]${self.usdc_amount + self.fee:.2f}[/] | [{action_color}]{self.action}[/]")
        table.add_row(f"[{market_color}]{self.market_name}[/] | [{side_color}]{self.side}[/]")
        table.add_row(f"Shares: [blue]{self.shares:.1f}[/] | [{side_color}]{self.price_per_share * 100: .0f}¢[/]")
        table.add_row()
        table.add_row(f"Token Id: [blue]{self.tokenId}[/]")
        table.add_row(f"Condition Id: [blue]{self.conditionId}[/]")
        table.add_row(f"Wallet: [blue]{self.wallet}[/]")
        table.add_row(f"Timestamp: [blue]{datetime.fromtimestamp(self.timestamp)}[/]")
        table.add_row()
        if self.detection_time:
            table.add_row(f"Time: [blue]{datetime.fromtimestamp(self.detection_time)}[/]")
        panel = Panel(
            table,
            title="[bold blue]Transaction[/bold blue]",
            border_style="bright_blue",
            expand=False,
        )

        console.print(panel)


@dataclass
class Position: 
    tokenId: str
    conditionId: str
    market_name: str
    slug: str

    wallet: str
    side: Side

    shares: float
    usdc_amount: float
    total_trades: int

    @property
    def price_per_share(self):
        return self.usdc_amount / self.shares if self.shares != 0 else 0.0
    
    def display(self):
        #set colors
        market_color = getMarketColor(self.market_name)
        side_color = ColorMap.GREEN if self.side == "up" else ColorMap.RED

        table = Table(
            show_header=False,
            box=box.SIMPLE_HEAVY,
            padding=(0, 2),
        )

        table.add_column("Field", style="bold", width=18)
        table.add_column("Value", style="blue")

        table.add_row("Market", f"[{market_color}]{self.market_name}[/]")
        table.add_row("Side", f"[bold {side_color}]{self.side}[/]")
        table.add_row("USDC Amount", f"[yellow]${self.usdc_amount:,.2f}[/yellow]")
        table.add_row("Shares", f"[magenta]{self.shares:,.1f}[/magenta]")
        table.add_row("Price / Share", f"[cyan]{self.price_per_share*100:.1f}¢[/cyan]")
        table.add_row("Total Trades", f"[bold]{self.total_trades:,}[/bold]")
        table.add_row()
        table.add_row("Token Id", f"[dim]{self.tokenId}[/dim]")
        table.add_row("Condition Id", f"{self.conditionId}")
        panel = Panel(
            table,
            title="[bold blue]Position[/bold blue]",
            border_style="bright_blue",
            expand=False,
        )

        console.print(panel)

@dataclass
class Market:
    upPos: Position | None
    downPos: Position | None
    outcome: marketOutcome

    def display(self):
        #market_color = getMarketColor(self.upPos.market_name)
        #outcome_color = ColorMap.GREEN if self.outcome == "up" else ColorMap.RED
        
        market_name = self.upPos.market_name if self.upPos else self.downPos.market_name
        market_color = getMarketColor(market_name)

        if self.outcome == "up":
            outcome_color = ColorMap.GREEN
        elif self.outcome == "down":
            outcome_color = ColorMap.RED
        else:
            outcome_color = ColorMap.ORANGE # unresolved / pending

        total_invested = sum(p.usdc_amount for p in (self.upPos, self.downPos) if p is not None)

        payout = 0.0
        if self.outcome == "up" and self.upPos is not None:
            payout = self.upPos.shares
        elif self.outcome == "down" and self.downPos is not None:
            payout = self.downPos.shares

        pnl = payout - total_invested
        pnl_pct = (pnl / total_invested * 100) if total_invested else 0.0
        pnl_color = ColorMap.GREEN if pnl >= 0 else ColorMap.RED
        sign = "+" if pnl >= 0 else ""

        table = Table(show_header=False, box=box.SIMPLE_HEAVY, padding=(0, 2))
        table.add_column("Field", style="bold", width=18)
        table.add_column("Value", style="blue")

        table.add_row("Market", f"[{market_color}]{market_name}[/]")
        table.add_row("Outcome", f"[bold {outcome_color}]{self.outcome}[/]")
        table.add_row()
        table.add_row("Total Invested", f"[yellow]${total_invested:,.2f}[/yellow]")
        table.add_row("Payout", f"[cyan]${payout:,.2f}[/cyan]")
        table.add_row("P/L", f"[bold {pnl_color}]{sign}${pnl:,.2f}[/]")
        table.add_row("P/L %", f"[bold {pnl_color}]{sign}{pnl_pct:.1f}%[/]")
        table.add_row()

        if self.upPos:
            table.add_row(
                "Up Shares",
                f"[green]{self.upPos.shares:,.1f}[/green] @ [green]{self.upPos.price_per_share*100:.1f}¢[/green] "
                f"(${self.upPos.usdc_amount:,.2f})",
            )
        if self.downPos:
            table.add_row(
                "Down Shares",
                f"[red]{self.downPos.shares:,.1f}[/red] @ [red]{self.downPos.price_per_share*100:.1f}¢[/red] "
                f"(${self.downPos.usdc_amount:,.2f})",
            )

        panel = Panel(
            table,
            title="[bold blue]Market Summary[/bold blue]",
            border_style=pnl_color,
            expand=False,
        )
        console.print(panel)

@dataclass
class Metadata:
    start_time: int
    end_time: int
    wallet: str
    market_filter: str
    id_map_path: str
    session_logs_path: str

def list_metadata_files():
    """returns a list of all metadata files in the 'BASE_PATH_METADATA' folder"""
    return [fileName for fileName in os.listdir(BASE_PATH_METADATA) if ".json" in fileName]  

def save_metadata(metadata: Metadata, timestamp: int) -> str:
    """saves metadata object in a json file and returns the file path"""
    filePath = f"{BASE_PATH_METADATA}/{timestamp}-metadata.json"
    saveAsJSON(metadata, filePath)
    return filePath

def load_metadata(file_path):
    json_dict = loadJSON(file_path)
    return Metadata(**json_dict)

def save_trades(trades: Trades, timestamp: int) -> str:
    """saves trades in a json file and returns the file path"""
    filePath = f"{BASE_PATH_LOGS}/{timestamp}-logs.json"
    saveAsJSON(trades, filePath)
    return filePath

def load_trades(path: str) -> Trades:
    """returns a list of trade objects from a json file"""
    with open(path, "r") as file:
        data = json.load(file)
    return {key: Trade(**elem) for key, elem in data.items()}

def init_trade(tx_hash: str, tx: Transaction, idMap: IdMap, detection_time: float = 0.0) -> Trade:
    token_id = tx.token_id       
    # Get market info
    market_name = "Unknown Market"
    slug = "Unknown Market"
    side = "unknown"
    conditionId = "Unknown"
    
    if token_id and token_id in idMap:
        market_name = idMap[token_id].question
        side = idMap[token_id].side
        slug = idMap[token_id].slug
        conditionId = idMap[token_id].conditionId

    return Trade(
        tx_hash=tx_hash,
        tokenId=token_id,
        conditionId=conditionId,
        wallet=tx.wallet,
        market_name=market_name,
        slug=slug,
        side=side,
        action=tx.action,
        usdc_amount=tx.usdc_amount,
        fee=tx.fee,
        shares=tx.shares,
        price_per_share=tx.usdc_amount / tx.shares,
        timestamp=tx.timestamp,
        detection_time=detection_time
    )

def sort_dict(dictionary: dict):
    keys = sorted(dictionary.keys())
    return {k: dictionary[k] for k in keys}

def display(collection: Trades | Positions | Markets):
    collection = sort_dict(collection)
    for obj in collection.values():
        if hasattr(obj, "display"):
            obj.display()

type Transactions = dict[str, Transaction]
type Trades = dict[str, Trade]
type Positions = dict[str, Position]
type Markets = dict[str, Market]
type IdMap = dict[str, MarketData]