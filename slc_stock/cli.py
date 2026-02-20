import json
from datetime import date

import click

import slc_stock.providers.yfinance_provider  # noqa: F401 — register providers
import slc_stock.providers.alpha_vantage_provider  # noqa: F401
import slc_stock.providers.polygon_provider  # noqa: F401
from slc_stock.config import DEFAULT_PROVIDER
from slc_stock.logging_config import setup_logging
from slc_stock.providers import list_providers
from slc_stock.service import QuoteService


@click.group()
def cli():
    """slc-stock — local stock quote CLI."""
    setup_logging()


@cli.command()
@click.argument("symbol")
@click.option("--years", default=3, help="Years of history to fetch.")
@click.option("--provider", default=DEFAULT_PROVIDER, help="Data provider to use.")
def prefetch(symbol: str, years: int, provider: str):
    """Download historical quotes into the local database."""
    svc = QuoteService()
    end = date.today()
    start = date(end.year - years, end.month, end.day)

    click.echo(f"Fetching {years}y of {symbol.upper()} from {provider} …")
    count = svc.prefetch(symbol, start, end, provider_name=provider)
    click.echo(f"Stored {count} quotes.")


@cli.command("prefetch-all")
@click.argument("symbol")
@click.option("--years", default=3, help="Years of history to fetch.")
def prefetch_all(symbol: str, years: int):
    """Download history from every configured provider."""
    svc = QuoteService()
    end = date.today()
    start = date(end.year - years, end.month, end.day)

    for name, prov in list_providers().items():
        if not prov.is_configured():
            click.echo(f"  {name}: skipped (not configured)")
            continue
        click.echo(f"  {name}: fetching …", nl=False)
        count = svc.prefetch(symbol, start, end, provider_name=name)
        click.echo(f" {count} quotes stored.")


@cli.command()
def providers():
    """List available data providers and their status."""
    for name, prov in list_providers().items():
        status = "ready" if prov.is_configured() else "needs API key"
        click.echo(f"  {name}: {status}")


@cli.command()
@click.argument("symbol")
@click.argument("date_str")
def compare(symbol: str, date_str: str):
    """Show data from all providers for a given symbol and date."""
    svc = QuoteService()
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        click.echo(f"Invalid date format: {date_str}. Use YYYY-MM-DD.", err=True)
        raise SystemExit(1)
    results = svc.get_quote_all_providers(symbol, day)

    if not results:
        click.echo(f"No data for {symbol.upper()} on {date_str} from any provider.")
        return

    header = f"{'Provider':<16} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>14}"
    click.echo(header)
    click.echo("-" * len(header))
    for q in results:
        click.echo(
            f"{q['provider']:<16} {q['open']:>10.2f} {q['high']:>10.2f} "
            f"{q['low']:>10.2f} {q['close']:>10.2f} {q['volume']:>14.0f}"
        )


@cli.command()
@click.option("--output", "-o", default="quotes.json", help="Output file path.")
def dump(output: str):
    """Export the entire database to a JSON file."""
    svc = QuoteService()
    records = svc.dump_database()
    with open(output, "w") as f:
        json.dump(records, f, indent=2)
    click.echo(f"Dumped {len(records)} quotes to {output}")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
def load(file: str):
    """Import quotes from a JSON file into the database."""
    svc = QuoteService()
    with open(file) as f:
        records = json.load(f)
    count = svc.load_database(records)
    click.echo(f"Loaded {count} quotes from {file}")


if __name__ == "__main__":
    cli()
