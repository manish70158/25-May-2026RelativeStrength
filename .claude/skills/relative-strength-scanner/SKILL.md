---
name: relative-strength-scanner
description: "Scan Nifty 500 stocks for relative strength vs Nifty index to identify outperformers. Use this skill when the user wants to run a relative strength scan, find stocks outperforming Nifty, identify momentum leaders in Indian markets, or asks about relative strength analysis for NSE stocks. Also trigger when users mention 'RS scan', 'relative strength ranking', 'Nifty outperformers', 'momentum screening', or want to compare stock performance against the Nifty benchmark."
---

# Dual-Period Relative Strength Scanner for Nifty 500

This skill runs a Python-based relative strength scanner against all Nifty 500 stocks, comparing each stock's performance to the Nifty 50 index over **two periods simultaneously: 101 days and 123 days**. It identifies stocks that are outperforming the benchmark in **BOTH periods** — ensuring multi-timeframe confirmation of relative strength.

## The Formula

The relative strength calculation mirrors the Pine Script logic:

```
RS = (Stock_Price_Today / Stock_Price_N_days_ago) / (Nifty_Today / Nifty_N_days_ago) - 1
```

- RS > 0 means the stock outperformed Nifty over the period
- RS < 0 means underperformance
- The RS MA (moving average of RS) shows the trend of relative strength

## Dual-Period Filter

**Key Feature**: A stock is marked as **OUTPERFORM** only if it satisfies the condition in **BOTH** the 101-day and 123-day periods:
- RS > 0 AND RS > RS_MA for the 101-day period
- RS > 0 AND RS > RS_MA for the 123-day period

This dual-period confirmation filters out stocks with inconsistent relative strength across timeframes.

## How to Use

### Quick Scan (Default Parameters)

Run the scanner with default settings (101-day and 123-day periods, 10-day MA):

```bash
python /path/to/scripts/relative_strength_scanner.py
```

### Custom Parameters

```bash
python /path/to/scripts/relative_strength_scanner.py --period-1 101 --period-2 123 --ma-period 10 --top 30
```

Available arguments:
- `--period-1` — First lookback period in trading days (default: 101)
- `--period-2` — Second lookback period in trading days (default: 123)
- `--ma-period` — Moving average period for RS smoothing (default: 10)
- `--top` — Number of top outperformers to display (default: 20)
- `--output` — Output CSV file path (default: `rs_scan_results.csv`)
- `--benchmark` — Benchmark symbol (default: `^NSEI` for Nifty 50)
- `--min-rs` — Minimum RS value to include in results (default: 0.0)
- `--show-all` — Show all 500 stocks, not just top N

### Output

The scanner produces:

1. **Console output** — Top N outperformers with RS values for both periods, RS MAs, and signal
2. **CSV file** — Full results saved to `rs_scan_results.csv` with columns:
   - `symbol` — NSE trading symbol
   - `name` — Company name
   - `close` — Latest closing price
   - `rs_value_101` — Relative strength value for 101-day period
   - `rs_ma_101` — Moving average of RS for 101-day period
   - `rs_value_123` — Relative strength value for 123-day period
   - `rs_ma_123` — Moving average of RS for 123-day period
   - `rs_avg` — Average RS across both periods (used for ranking)
   - `signal` — OUTPERFORM, NEUTRAL, or UNDERPERFORM
   - `rs_trend` — Combined trend: UP, DOWN, or MIXED
   - `trend_detail` — Individual trends for each period (e.g., "UP/UP", "UP/DOWN")
   - `scan_date` — Date of scan

### Signal Logic

- **OUTPERFORM**: Stock must satisfy BOTH conditions:
  - 101-day: RS > 0 AND RS > RS_MA
  - 123-day: RS > 0 AND RS > RS_MA
  - (Stock is beating Nifty with rising momentum in BOTH periods)

- **NEUTRAL**: RS > 0 in both periods but doesn't meet the OUTPERFORM criteria
  - (Beating Nifty but may be losing momentum in one or both periods)

- **UNDERPERFORM**: RS < 0 in either period
  - (Lagging behind Nifty in at least one timeframe)

### Telegram Alerts

The scanner tracks which stocks are outperforming between runs. When a stock *newly* enters the OUTPERFORM category (wasn't there in the previous scan), it sends a Telegram alert.

**First-time setup:**

```bash
python scripts/relative_strength_scanner.py --setup-telegram
```

This will guide you through creating a Telegram bot and saving credentials. You need:
1. A bot token from @BotFather on Telegram
2. Your chat ID (the bot will test the connection)

**Running with alerts:**

```bash
python scripts/relative_strength_scanner.py --alert
```

The first run with `--alert` creates a baseline (no alert fires). From the second run onwards, it compares against the previous scan and alerts on new outperformers.

**How it works:**
- Run 1: Saves 168 outperforming stocks as baseline
- Run 2 (next day): If 5 new stocks entered OUTPERFORM that weren't there yesterday, you get an alert listing those 5 stocks with their RS values

**Override credentials per-run (useful for cron):**

```bash
python scripts/relative_strength_scanner.py --alert --bot-token "YOUR_TOKEN" --chat-id "YOUR_CHAT_ID"
```

### Daily Automation

To run this daily after market close with alerts, set up a cron job:

```bash
# Run at 4:30 PM IST (after market close) on weekdays with alerts
30 16 * * 1-5 cd /path/to/project && python scripts/relative_strength_scanner.py --alert --output "scans/rs_$(date +\%Y\%m\%d).csv"
```

Or use the scheduling helper:

```bash
python scripts/relative_strength_scanner.py --setup-cron
```

## Dependencies

Install required packages:

```bash
pip install -r scripts/requirements.txt
```

## Data Source

- Uses **yfinance** for historical price data
- Nifty 500 stock list is fetched from NSE India (cached locally and refreshed weekly)
- Benchmark default is `^NSEI` (Nifty 50 Index)

## Interpreting Results

When discussing results with the user:
- **Dual-period confirmation**: Stocks marked as OUTPERFORM have passed the filter in BOTH 101-day and 123-day periods, providing multi-timeframe validation
- Stocks with RS > 0.10 in both periods are showing strong outperformance (10%+ better than Nifty)
- **Best candidates**: Look for stocks where BOTH RS values are positive AND trending up (RS > RS_MA in both periods) — these have confirmed momentum across timeframes
- A stock with high RS in one period but RS < RS_MA in the other may be losing momentum or showing divergence between timeframes
- **Trend detail**: The "UP/UP" trend indicates rising RS in both periods (strongest confirmation), while "MIXED" suggests divergence worth investigating
- Negative RS in either period automatically excludes a stock from the OUTPERFORM category, ensuring only consistently strong performers are highlighted

## Script Location

The main scanner script is at: `scripts/relative_strength_scanner.py`
