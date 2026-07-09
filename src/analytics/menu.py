from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich import box
from rich import prompt

from datetime import datetime

console = Console()

def getIntInput(msg: str, error_msg = "Invalid! Please try again", num_range: tuple[int | float, int | float] = (float("-Inf"), float("Inf"))):
    err_style = "bold red"
    while True:
        user_input = prompt.Prompt().ask(msg)

        if str.isdigit(user_input):
            user_input = int(user_input)
            if num_range[0] <= user_input <= num_range[1]:
                return user_input
        console.print(f"[{err_style}]{error_msg}[/]")
        

def selectFileMenu(fileNames: list[str]):
    def render():
        table = Table(
            title="[cyan]Session log files[/cyan]",
            box=box.SIMPLE_HEAVY,
            show_header=False,
            padding=(0, 0),
        )

        table.add_column("Number", style="bold")
        table.add_column("file_name", style="yellow bold")
        table.add_column("date", style="#FFA500 bold")

        for i, fileName in enumerate(fileNames):
            timestamp, _ = fileName.split("-")
            isoDate = str(datetime.fromtimestamp(int(timestamp)))
            table.add_row(str(i + 1), fileName, isoDate)

        console.print(table)
    render()

    user_selection = getIntInput("[cyan]Select a session log file by number", num_range=(1, len(fileNames)))
    return fileNames[user_selection - 1]

def selectActionMenu(actions: list[str]):
    def render():
        table = Table(
            box=box.SIMPLE_HEAVY,
            show_header=False,
            padding=(0, 0),
        )

        table.add_column("Number", style="bold")
        table.add_column("action", style="cyan bold")

        for i, action in enumerate(actions):
            table.add_row(str(i + 1), action)

        panel = Panel(
            table,
            title="[bold blue]Actions[/bold blue]",
            border_style="bright_blue",
            expand=False,
        )

        console.print(panel)
    render()

    user_selection = getIntInput("[cyan]Select an action by number", num_range=(1, len(actions)))
    return actions[user_selection - 1]