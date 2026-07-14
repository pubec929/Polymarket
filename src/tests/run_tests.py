from rich import print
from rich.console import Console

from src.tests.manage_hex_data import get_hex_data
from src.tests.manage_tests import load_test_cases

from rich.table import Table
from rich.panel import Panel
from rich import box

import time

def _diff_transactions(expected, actual):
    """Yields (field, expected_value, actual_value) for any mismatched fields."""
    for field, exp_val in expected.__dict__.items():
        got_val = getattr(actual, field, "[missing]")
        if exp_val != got_val:
            yield field, exp_val, got_val


console = Console()

def test_hex_parser(parse_hex_data):
    test_cases = load_test_cases()
    total_tests = 0
    passed = 0
    failed_tests = []
 

    results_table = Table(
        title="Hex Parser Test Run",
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
 
    start_time = time.perf_counter()
    with console.status("[bold cyan]Running tests...", spinner="dots") as status:
        for test_case in test_cases:
            tx_hash = test_case.tx_hash
            transaction = test_case.tx
            print(tx_hash, transaction)
            total_tests += 1
            hex_data = get_hex_data(tx_hash)
            parsed= parse_hex_data(hex_data, transaction.wallet)
            if parsed == transaction:
                passed += 1
                results_table.add_row(
                    str(total_tests),
                    tx_hash,
                    "[bold green]PASS[/bold green]",
                    "", "", "",
                )
            else:
                failed_tests.append(tx_hash)
                first_row = True
                for field, exp, got in _diff_transactions(transaction, parsed):
                    results_table.add_row(
                        str(total_tests) if first_row else "",
                        tx_hash if first_row else "",
                        "[bold red]FAIL[/bold red]" if first_row else "",
                        field,
                        str(exp),
                        str(got),
                        
                    )
                    first_row = False
 
            status.update(f"[bold cyan]Running tests... ({total_tests}/{len(test_cases)})")
 
    console.print()
    console.print(results_table)
    console.print()
 
    # Summary panel
    fail_count = len(failed_tests)
    pass_rate = (passed / total_tests * 100) if total_tests else 0
    status_color = "green" if fail_count == 0 else "red"
    verdict = "ALL PASSED" if fail_count == 0 else f"{fail_count} FAILED"
 
    summary = Table.grid(padding=(0, 4))
    summary.add_column(justify="center")
    summary.add_column(justify="center")
    summary.add_column(justify="center")
    summary.add_column(justify="center")
    summary.add_row(
        f"[dim]Total[/dim]\n[bold white]{total_tests}[/bold white]",
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

    # List failed tests if any
    if failed_tests:
        console.print("[bold red]Failed test transaction hashes:[/bold red]")
        for tx_hash in failed_tests:
            console.print(f"  [red]{tx_hash}[/red]")
        console.print()

    # Time stats
    total_time = time.perf_counter() - start_time
    avg_time = total_time / total_tests if total_tests else 0

    time_summary = Table.grid(padding=(0, 4))
    time_summary.add_column(justify="center")
    time_summary.add_column(justify="center")
    time_summary.add_row(
        f"[dim]Total time[/dim]\n[bold white]{total_time:.3f}s[/bold white]",
        f"[dim]Average / test[/dim]\n[bold cyan]{avg_time * 1000:.2f} ms[/bold cyan]",
    )

    console.print(
        Panel(
            time_summary,
            title="[bold cyan] Timing [/bold cyan]",
            border_style="cyan",
            padding=(1, 4),
        )
    )

def main():
    from src.parsers.hex_parser import parse_calldata

    test_hex_parser(parse_calldata)
    
if __name__ == "__main__":
    main()