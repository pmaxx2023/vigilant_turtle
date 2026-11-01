from __future__ import annotations

import json
import sys

import httpx
import typer
from rich.console import Console
from rich.table import Table

from .arbitrage import find_opportunities
from .models import Opportunity
from .sources import DemoSource, EbayBrowseSource
from .sources.ebay import EbayAuthError

app = typer.Typer(
    add_completion=False,
    help="vigilant_turtle - find eBay arbitrage opportunities by spotting listings priced well below the median.",
)
console = Console()


def _build_source(source_name: str):
    if source_name == "demo":
        return DemoSource()
    if source_name == "ebay":
        try:
            return EbayBrowseSource()
        except EbayAuthError as err:
            console.print(f"[bold red]error:[/] {err}")
            console.print(
                "Get free credentials at https://developer.ebay.com/ and set "
                "EBAY_CLIENT_ID / EBAY_CLIENT_SECRET, or use --source demo."
            )
            raise typer.Exit(code=2) from err
    raise typer.BadParameter(f"unknown source: {source_name}")


def _http_error_message(err: httpx.HTTPError) -> str:
    if isinstance(err, httpx.HTTPStatusError):
        resp = err.response
        msg = f"eBay returned {resp.status_code} {resp.reason_phrase}."
        if resp.status_code in (401, 403):
            msg += " Check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET."
        elif resp.status_code == 429:
            msg += " You hit the eBay rate limit. Wait a bit and try again."
        return msg
    return f"Could not reach eBay: {str(err) or type(err).__name__}"


def _render_table(keyword: str, opps: list[Opportunity]) -> None:
    if not opps:
        console.print(
            f"No arbitrage opportunities found for [bold]{keyword}[/] at the current threshold."
        )
        return

    median = opps[0].median_price
    sample = opps[0].sample_size
    console.print(
        f"\n[bold green]{len(opps)}[/] opportunit{'y' if len(opps) == 1 else 'ies'} "
        f"for [bold]{keyword}[/]  "
        f"(median landed: ${median:,.2f}, sample size: {sample})\n"
    )

    table = Table(show_lines=False, header_style="bold cyan")
    table.add_column("Discount", justify="right")
    table.add_column("Landed", justify="right")
    table.add_column("Est. Profit", justify="right")
    table.add_column("Condition")
    table.add_column("Seller")
    table.add_column("Title", overflow="fold")

    for opp in opps:
        table.add_row(
            f"{opp.spread_pct * 100:5.1f}%",
            f"${opp.listing.landed_price:,.2f}",
            f"${opp.profit_estimate:,.2f}",
            opp.listing.condition or "-",
            opp.listing.seller or "-",
            opp.listing.title,
        )
    console.print(table)


@app.command()
def scan(
    keyword: str = typer.Argument(..., help="Product keyword to search for."),
    source: str = typer.Option("demo", "--source", "-s", help="Data source: 'demo' or 'ebay'."),
    threshold: float = typer.Option(
        0.20, "--threshold", "-t", min=0.0, max=1.0,
        help="Required discount vs median, as a fraction (0.20 = 20%).",
    ),
    limit: int = typer.Option(50, "--limit", "-n", min=1, max=200, help="Max listings to fetch."),
    min_sample: int = typer.Option(5, "--min-sample", help="Minimum listings before flagging."),
    min_profit: float = typer.Option(0.0, "--min-profit", help="Minimum estimated profit per unit."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Scan a marketplace for listings priced well below the median for KEYWORD."""
    src = _build_source(source)
    try:
        listings = src.search(keyword, limit=limit)
    except EbayAuthError as err:
        console.print(f"[bold red]error:[/] {err}. Check EBAY_CLIENT_ID and EBAY_CLIENT_SECRET.", soft_wrap=True)
        raise typer.Exit(code=1) from err
    except httpx.HTTPError as err:
        console.print(f"[bold red]error:[/] {_http_error_message(err)}", soft_wrap=True)
        raise typer.Exit(code=1) from err
    opps = find_opportunities(
        listings,
        threshold_pct=threshold,
        min_sample=min_sample,
        min_profit=min_profit,
    )

    if as_json:
        json.dump([o.model_dump(mode="json") for o in opps], sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    if not listings:
        console.print(f"[yellow]No listings returned from source '{source}' for '{keyword}'.[/]")
        if source == "demo":
            available = DemoSource().available_keywords()
            console.print("Try one of: " + ", ".join(f"[bold]{k}[/]" for k in available))
        return

    _render_table(keyword, opps)


@app.command()
def keywords() -> None:
    """List the keywords bundled in the demo source."""
    for k in DemoSource().available_keywords():
        console.print(f"- {k}")


if __name__ == "__main__":
    app()
