# vigilant_turtle

A small CLI that hunts for **eBay arbitrage opportunities** by spotting active
listings priced significantly below the median for a given keyword.

The idea: for any popular product, the going rate on eBay clusters around a
median landed price (item + shipping). Listings that sit well below that median
are candidates for retail arbitrage — buy them, resell them at the going rate.

## Install

Requires Python 3.11+.

```bash
pip install -e .
```

This exposes a `vt` command.

## Quick start (no credentials needed)

```bash
vt scan "airpods pro" --source demo
vt scan "nintendo switch oled" --source demo --threshold 0.15
vt keywords
```

The `demo` source ships with a small bundled dataset so the tool runs without
any API keys.

## Live eBay data

Create a free eBay developer account at <https://developer.ebay.com/> and grab a
production App ID + Cert ID. Then:

```bash
export EBAY_CLIENT_ID=your_app_id
export EBAY_CLIENT_SECRET=your_cert_id
vt scan "airpods pro" --source ebay --threshold 0.25 --limit 100
```

Optional: `EBAY_MARKETPLACE` (defaults to `EBAY_US`).

## Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--source / -s` | `demo` | Data source: `demo` or `ebay`. |
| `--threshold / -t` | `0.20` | Required discount vs median (`0.20` = 20%). |
| `--limit / -n` | `50` | Max listings to fetch. |
| `--min-sample` | `5` | Minimum listings before flagging anything. |
| `--min-profit` | `0` | Drop opportunities below this estimated profit per unit. |
| `--json` | off | Emit JSON instead of a table (pipe-friendly). |

## How it works

1. Fetch listings for a keyword from the selected source.
2. Compute the **median landed price** (`price + shipping`) across the sample.
3. Flag any listing whose landed price is at least `threshold` below median.
4. Sort by discount % and render as a table (or JSON).

This is a simple, transparent signal — it's noisy by design. Combine it with:
- Title fuzzy-matching to weed out accessories / wrong variants.
- Sold-price history (eBay Marketplace Insights API) for stronger fair-value.
- Seller reputation filters.

The codebase is structured to make those extensions straightforward — sources
are pluggable via the `Source` protocol in `src/vigilant_turtle/sources/base.py`.

## Project layout

```
src/vigilant_turtle/
  cli.py              # typer entry point ("vt" command)
  arbitrage.py        # median + outlier detection
  models.py           # Listing, Opportunity (pydantic)
  sources/
    base.py           # Source protocol
    demo.py           # bundled offline data
    demo_data.json
    ebay.py           # live eBay Browse API client
```

## Disclaimer

This is a research / educational tool. It does not place orders, does not give
financial advice, and ignores eBay fees, taxes, and shipping you'd actually pay
to resell. Always verify before buying.
