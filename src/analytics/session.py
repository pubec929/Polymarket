from json import load, loads

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.parsers.log_parser import analyze_logs, load_logs
from src.types import Trade, Trades

console = Console()

def load_session(file_path) -> Trades:
    with open(file_path, "r") as file:
        data = load(file)

    return {key: Trade(**loads(elem)) for key, elem in data.items()}


def _diff_trade(expected: Trade, got):
    checks = [
        ("Shares", expected.shares, got.shares),
        ("USDC Amount", expected.usdc_amount, got.usdc_amount),
    ]

    for field, exp, actual in checks:
        if exp != actual:
            yield field, exp, actual


def evaluate(file_path):
    trades = load_session(file_path)

    total = 0
    passed = 0
    failed_trades = []

    results_table = Table(
        title="Session Evaluation",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold dim",
        border_style="dim",
    )

    results_table.add_column("#", style="dim", width=4, justify="right")
    results_table.add_column("TX Hash", style="cyan", no_wrap=True)
    results_table.add_column("Status", justify="center", width=10)
    results_table.add_column("Field", style="dim")
    results_table.add_column("Expected", style="green")
    results_table.add_column("Got", style="red")

    with console.status("[bold cyan]Evaluating session...", spinner="dots") as status:
        for trade in trades.values():
            total += 1
            logs = load_logs(trade.tx_hash)
            transaction = analyze_logs(logs, trade.wallet)
            trade.usdc_amount = round(trade.usdc_amount, 2)
            trade.shares = round(trade.shares, 1)
            differences = list(_diff_trade(trade, transaction))

            if not differences:
                passed += 1
                results_table.add_row(
                    str(total),
                    trade.tx_hash,
                    "[bold green]PASS[/bold green]",
                    "",
                    "",
                    "",
                )
            else:
                failed_trades.append(trade.tx_hash)

                first_row = True
                for field, expected, got in differences:
                    results_table.add_row(
                        str(total) if first_row else "",
                        trade.tx_hash if first_row else "",
                        "[bold red]FAIL[/bold red]" if first_row else "",
                        field,
                        str(expected),
                        str(got),
                    )
                    first_row = False

            status.update(f"[bold cyan]Evaluating session... ({total}/{len(trades)})")

    console.print()
    console.print(results_table)
    console.print()

    fail_count = len(failed_trades)
    pass_rate = (passed / total * 100) if total else 0
    status_color = "green" if fail_count == 0 else "red"
    verdict = "ALL PASSED" if fail_count == 0 else f"{fail_count} FAILED"

    summary = Table.grid(padding=(0, 4))
    summary.add_column(justify="center")
    summary.add_column(justify="center")
    summary.add_column(justify="center")
    summary.add_column(justify="center")

    summary.add_row(
        f"[dim]Total[/dim]\n[bold white]{total}[/bold white]",
        f"[dim]Passed[/dim]\n[bold green]{passed}[/bold green]",
        f"[dim]Failed[/dim]\n[bold red]{fail_count}[/bold red]",
        f"[dim]Pass rate[/dim]\n[bold]{pass_rate:.1f}%[/bold]",
    )

    console.print(Panel(
        summary,
        title=f"[bold {status_color}] {verdict} [/bold {status_color}]",
        border_style=status_color,
        padding=(1, 4),
    ))
    console.print()

    if failed_trades:
        console.print("[bold red]Failed session transaction hashes:[/bold red]")
        for tx_hash in failed_trades:
            console.print(f"  [red]{tx_hash}[/red]")
        console.print()
