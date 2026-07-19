from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.utils.colors import getMarketColor 
from src.types import Market, Position, Markets


console = Console()


def _position_summary(position: Position | None) -> str:
    if position is None:
        return "—"

    return (
        f"{position.shares:,.1f} @ {position.price_per_share * 100:.1f}¢ "
        f"(${position.usdc_amount:,.2f})"
    )


def compareMarkets(markets: Markets) -> None:
    """Display a collection of markets as a single comparison table."""
    table = Table(
        title="Market Comparison",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="bright_blue",
        row_styles=("", ""),
        show_lines=True,
    )

    table.add_column("Market", style="bold", overflow="fold")
    table.add_column("Outcome", justify="center", no_wrap=True)
    table.add_column("Invested", justify="right", no_wrap=True)
    table.add_column("Payout", justify="right", no_wrap=True)
    table.add_column("P/L", justify="right", no_wrap=True)
    table.add_column("P/L %", justify="right", no_wrap=True)
    table.add_column("Up position", style="green", justify="right", no_wrap=True)
    table.add_column("Down position", style="red", justify="right", no_wrap=True)

    for market in markets.values():
        positions = (market.upPos, market.downPos)
        market_name = next(
            (position.market_name for position in positions if position is not None),
            "Unknown Market",
        )

        market_style = getMarketColor(market_name)

        total_invested = sum(
            position.usdc_amount for position in positions if position is not None
        )

        payout = 0.0
        if market.outcome == "up" and market.upPos is not None:
            payout = market.upPos.shares
        elif market.outcome == "down" and market.downPos is not None:
            payout = market.downPos.shares

        pnl = payout - total_invested
        pnl_pct = pnl / total_invested * 100 if total_invested else 0.0
        pnl_style = "bold green" if pnl >= 0 else "bold red"
        outcome_style = {
            "up": "bold green",
            "down": "bold red",
        }.get(market.outcome, "bold yellow")

        table.add_row(
            Text(market_name, style=market_style),
            Text(str(market.outcome).upper(), style=outcome_style),
            f"${total_invested:,.2f}",
            f"${payout:,.2f}",
            Text(f"${pnl:+,.2f}", style=pnl_style),
            Text(f"{pnl_pct:+.1f}%", style=pnl_style),
            _position_summary(market.upPos),
            _position_summary(market.downPos),
        )

    if not markets:
        table.add_row("No markets to display", "", "", "", "", "", "", "")

    console.print(table)
