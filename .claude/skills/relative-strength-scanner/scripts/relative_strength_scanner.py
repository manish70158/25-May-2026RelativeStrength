#!/usr/bin/env python3
"""
Relative Strength Scanner for Nifty 500 Stocks

Replicates the Pine Script RS indicator logic:
  RS = (Stock_Today / Stock_N_ago) / (Nifty_Today / Nifty_N_ago) - 1

Scans all Nifty 500 stocks and ranks them by relative strength vs Nifty index.
"""

import argparse
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
import requests


# --- Configuration ---
NIFTY500_CACHE_FILE = Path(__file__).parent / "nifty500_symbols.json"
HISTORY_FILE = Path(__file__).parent / "previous_outperformers.json"
CONFIG_FILE = Path(__file__).parent / "config.json"
CACHE_MAX_AGE_DAYS = 7
DEFAULT_BENCHMARK = "^NSEI"
DEFAULT_PERIOD_1 = 101
DEFAULT_PERIOD_2 = 123
DEFAULT_MA_PERIOD = 10
DEFAULT_TOP = 20
DEFAULT_OUTPUT = "rs_scan_results.csv"


def fetch_nifty500_symbols() -> list[dict]:
    """Fetch Nifty 500 constituent list from NSE India."""

    # Check cache first
    if NIFTY500_CACHE_FILE.exists():
        cache_age = time.time() - NIFTY500_CACHE_FILE.stat().st_mtime
        if cache_age < CACHE_MAX_AGE_DAYS * 86400:
            with open(NIFTY500_CACHE_FILE) as f:
                return json.load(f)

    print("Fetching Nifty 500 stock list from NSE...")

    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/csv,application/csv,text/plain,*/*",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse CSV
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        symbols = []
        for _, row in df.iterrows():
            symbol = row.get("Symbol", row.get("symbol", ""))
            company = row.get("Company Name", row.get("company", ""))
            if symbol:
                symbols.append({
                    "symbol": str(symbol).strip(),
                    "name": str(company).strip() if company else symbol,
                    "yf_symbol": f"{str(symbol).strip()}.NS"
                })

        if symbols:
            with open(NIFTY500_CACHE_FILE, "w") as f:
                json.dump(symbols, f, indent=2)
            print(f"Cached {len(symbols)} symbols.")
            return symbols

    except Exception as e:
        print(f"Warning: Could not fetch from NSE ({e}). Trying alternate source...")

    # Fallback: try to load from a local file if provided
    local_file = Path(__file__).parent / "nifty500_manual.csv"
    if local_file.exists():
        df = pd.read_csv(local_file)
        symbols = []
        for _, row in df.iterrows():
            symbol = str(row.iloc[0]).strip()
            name = str(row.iloc[1]).strip() if len(row) > 1 else symbol
            symbols.append({
                "symbol": symbol,
                "name": name,
                "yf_symbol": f"{symbol}.NS"
            })
        return symbols

    # If cache exists but is stale, use it anyway
    if NIFTY500_CACHE_FILE.exists():
        print("Using stale cache as fallback.")
        with open(NIFTY500_CACHE_FILE) as f:
            return json.load(f)

    print("ERROR: Cannot get Nifty 500 list. Please provide nifty500_manual.csv")
    sys.exit(1)


def download_price_data(symbols: list[str], max_period_days: int, ma_period: int) -> dict[str, pd.Series]:
    """
    Download closing prices for all symbols.
    We need max_period + ma_period + buffer days of data.
    """
    # Need extra days for MA calculation and weekends/holidays
    total_days_needed = (max_period_days + ma_period + 10) * 2  # 2x buffer for non-trading days
    start_date = (datetime.now() - timedelta(days=total_days_needed)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Downloading price data for {len(symbols)} symbols...")
    print(f"Date range: {start_date} to {end_date}")

    # Download in batches to avoid timeout
    batch_size = 50
    all_data = {}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_str = " ".join(batch)

        try:
            data = yf.download(
                batch_str,
                start=start_date,
                end=end_date,
                progress=False,
                group_by="ticker",
                auto_adjust=True,
                threads=True
            )

            for sym in batch:
                try:
                    if len(batch) == 1:
                        close = data["Close"]
                    else:
                        close = data[sym]["Close"]

                    if close is not None and not close.empty and close.dropna().shape[0] > max_period_days:
                        all_data[sym] = close.dropna()
                except (KeyError, TypeError):
                    continue

        except Exception as e:
            print(f"  Warning: Batch {i//batch_size + 1} had issues: {e}")
            continue

        # Progress indicator
        done = min(i + batch_size, len(symbols))
        print(f"  Downloaded {done}/{len(symbols)} symbols...", end="\r")

    print(f"\n  Successfully got data for {len(all_data)} symbols.")
    return all_data


def calculate_relative_strength(
    stock_prices: pd.Series,
    benchmark_prices: pd.Series,
    period: int,
    ma_period: int
) -> dict:
    """
    Calculate RS value and RS MA.

    RS = (stock_today / stock_N_ago) / (benchmark_today / benchmark_N_ago) - 1
    RS_MA = SMA(RS, ma_period)
    """
    # Align dates
    common_idx = stock_prices.index.intersection(benchmark_prices.index)
    stock = stock_prices.loc[common_idx]
    bench = benchmark_prices.loc[common_idx]

    if len(stock) < period + ma_period:
        return None

    # Calculate RS for each day starting from index 'period' onwards
    rs_values = []
    for i in range(period, len(stock)):
        stock_return = stock.iloc[i] / stock.iloc[i - period]
        bench_return = bench.iloc[i] / bench.iloc[i - period]

        if bench_return == 0:
            continue

        rs = (stock_return / bench_return) - 1
        rs_values.append(rs)

    if len(rs_values) < ma_period:
        return None

    current_rs = rs_values[-1]
    rs_ma = sum(rs_values[-ma_period:]) / ma_period

    return {
        "rs_value": round(current_rs, 6),
        "rs_ma": round(rs_ma, 6),
        "close": round(float(stock.iloc[-1]), 2),
        "scan_date": stock.index[-1].strftime("%Y-%m-%d")
    }


def determine_signal(
    rs_value_101: float,
    rs_ma_101: float,
    rs_value_123: float,
    rs_ma_123: float
) -> tuple[str, str, str]:
    """
    Determine signal and trend based on RS values for BOTH periods.
    Stock must outperform in BOTH periods to be marked as OUTPERFORM.
    """
    # Check if outperforming in 101-day period
    outperform_101 = rs_value_101 > 0 and rs_value_101 > rs_ma_101

    # Check if outperforming in 123-day period
    outperform_123 = rs_value_123 > 0 and rs_value_123 > rs_ma_123

    # Signal logic: must outperform in BOTH periods
    if outperform_101 and outperform_123:
        signal = "OUTPERFORM"
    elif rs_value_101 > 0 and rs_value_123 > 0:
        signal = "NEUTRAL"
    else:
        signal = "UNDERPERFORM"

    # Determine trend for each period
    trend_101 = "UP" if rs_value_101 > rs_ma_101 else "DOWN"
    trend_123 = "UP" if rs_value_123 > rs_ma_123 else "DOWN"

    # Combined trend
    if trend_101 == "UP" and trend_123 == "UP":
        combined_trend = "UP"
    elif trend_101 == "DOWN" and trend_123 == "DOWN":
        combined_trend = "DOWN"
    else:
        combined_trend = "MIXED"

    return signal, combined_trend, f"{trend_101}/{trend_123}"


def load_config() -> dict:
    """Load Telegram config from config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save config to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_previous_outperformers() -> set:
    """Load the set of symbols that were outperforming in the previous scan."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            data = json.load(f)
            return set(data.get("outperformers", []))
    return set()


def save_current_outperformers(symbols: list[str]):
    """Save current outperformers for next scan comparison."""
    with open(HISTORY_FILE, "w") as f:
        json.dump({
            "outperformers": symbols,
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }, f, indent=2)


def send_telegram_alert(message: str, bot_token: str, chat_id: str) -> bool:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            print(f"  Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"  Telegram send failed: {e}")
        return False


def format_telegram_message(
    new_outperformers: list[dict],
    lost_outperformers: list[str],
    scan_date: str
) -> str:
    """Format the alert message for Telegram with both new and dropped stocks."""
    msg = f"<b>📊 RS Scanner Update</b> ({scan_date})\n"
    msg += "=" * 40 + "\n\n"

    # New outperformers section
    if new_outperformers:
        msg += f"<b>✅ NEW OUTPERFORMERS ({len(new_outperformers)})</b>\n"
        msg += f"<i>Stocks newly beating Nifty in BOTH periods</i>\n\n"

        for i, stock in enumerate(new_outperformers[:15], 1):
            rs_101_pct = stock["rs_value_101"] * 100
            rs_123_pct = stock["rs_value_123"] * 100
            msg += (
                f"{i}. <b>{stock['symbol']}</b> "
                f"| 101d: {rs_101_pct:+.1f}% "
                f"| 123d: {rs_123_pct:+.1f}%\n"
            )

        if len(new_outperformers) > 15:
            msg += f"<i>... and {len(new_outperformers) - 15} more</i>\n"
    else:
        msg += "<b>✅ NEW OUTPERFORMERS</b>\n"
        msg += "<i>None</i>\n"

    msg += "\n" + "-" * 40 + "\n\n"

    # Dropped outperformers section
    if lost_outperformers:
        msg += f"<b>⚠️ DROPPED FROM OUTPERFORM ({len(lost_outperformers)})</b>\n"
        msg += f"<i>No longer beating Nifty in both periods</i>\n\n"

        for i, symbol in enumerate(lost_outperformers[:15], 1):
            msg += f"{i}. {symbol}\n"

        if len(lost_outperformers) > 15:
            msg += f"<i>... and {len(lost_outperformers) - 15} more</i>\n"
    else:
        msg += "<b>⚠️ DROPPED FROM OUTPERFORM</b>\n"
        msg += "<i>None</i>\n"

    return msg


def check_and_alert(results: list[dict], bot_token: str = None, chat_id: str = None):
    """
    Compare current outperformers with previous scan.
    Send Telegram alert for newly added outperformers.
    """
    # Get current outperformers
    current_outperformers = [r for r in results if r["signal"] == "OUTPERFORM"]
    current_symbols = set(r["symbol"] for r in current_outperformers)

    # Load previous outperformers
    previous_symbols = load_previous_outperformers()

    # Find NEW outperformers (not in previous scan)
    new_symbols = current_symbols - previous_symbols

    # Save current state for next run
    save_current_outperformers(list(current_symbols))

    if not previous_symbols:
        print("\n  First scan — saved baseline. Alerts will fire from next scan onwards.")
        return

    # Get full details for new outperformers
    new_outperformers = [r for r in current_outperformers if r["symbol"] in new_symbols]
    new_outperformers.sort(key=lambda x: x["rs_avg"], reverse=True)

    # Also get stocks that dropped out of outperform
    lost_symbols = previous_symbols - current_symbols

    scan_date = results[0]["scan_date"] if results else datetime.now().strftime("%Y-%m-%d")

    # Console output
    if new_outperformers:
        print(f"\n  NEW OUTPERFORMERS: {len(new_outperformers)} stocks")
        print(f"  {'-'*50}")
        for s in new_outperformers[:10]:
            print(f"    {s['symbol']:<12} RS-101: {s['rs_value_101']:+.4f}  RS-123: {s['rs_value_123']:+.4f}  Close: {s['close']}")
        if len(new_outperformers) > 10:
            print(f"    ... and {len(new_outperformers) - 10} more")
    else:
        print("\n  No new outperformers since last scan.")

    if lost_symbols:
        print(f"\n  DROPPED FROM OUTPERFORM: {len(lost_symbols)} stocks")
        for sym in list(lost_symbols)[:5]:
            print(f"    {sym}")
        if len(lost_symbols) > 5:
            print(f"    ... and {len(lost_symbols) - 5} more")
    else:
        print("\n  No stocks dropped from outperform.")

    # If no changes at all, don't send alert
    if not new_symbols and not lost_symbols:
        print("\n  No changes since last scan — skipping alert.")
        return

    # Send Telegram alert (always send if there are changes OR if it's the first scan after baseline)
    if not bot_token or not chat_id:
        config = load_config()
        bot_token = bot_token or config.get("telegram_bot_token")
        chat_id = chat_id or config.get("telegram_chat_id")

    if bot_token and chat_id:
        # Send alert if there are new outperformers, dropped stocks, or neither (just status update)
        message = format_telegram_message(new_outperformers, list(lost_symbols), scan_date)
        print(f"\n  Sending Telegram alert...")
        if send_telegram_alert(message, bot_token, chat_id):
            print("  Telegram alert sent!")
        else:
            print("  Failed to send Telegram alert.")
    else:
        print("\n  Telegram not configured. Run with --setup-telegram to configure.")


def setup_telegram():
    """Interactive setup for Telegram bot credentials."""
    print("\n" + "=" * 60)
    print("  TELEGRAM ALERT SETUP")
    print("=" * 60)
    print()
    print("  Steps to create a Telegram bot:")
    print("  1. Open Telegram and search for @BotFather")
    print("  2. Send /newbot and follow instructions")
    print("  3. Copy the bot token (looks like 123456:ABC-DEF...)")
    print()
    print("  To get your Chat ID:")
    print("  1. Send any message to your new bot")
    print("  2. Open: https://api.telegram.org/bot<TOKEN>/getUpdates")
    print("  3. Find 'chat':{'id': YOUR_CHAT_ID}")
    print()

    bot_token = input("  Enter Bot Token: ").strip()
    chat_id = input("  Enter Chat ID: ").strip()

    if not bot_token or not chat_id:
        print("  Aborted — both token and chat ID are required.")
        return

    # Test the connection
    print("\n  Testing connection...")
    test_msg = "RS Scanner connected! You'll receive alerts when new stocks start outperforming Nifty."
    if send_telegram_alert(test_msg, bot_token, chat_id):
        print("  Test message sent successfully!")
        config = load_config()
        config["telegram_bot_token"] = bot_token
        config["telegram_chat_id"] = chat_id
        save_config(config)
        print(f"  Config saved to: {CONFIG_FILE}")
    else:
        print("  Test failed. Please check your token and chat ID.")


def run_scan(
    period_1: int = DEFAULT_PERIOD_1,
    period_2: int = DEFAULT_PERIOD_2,
    ma_period: int = DEFAULT_MA_PERIOD,
    top: int = DEFAULT_TOP,
    output: str = DEFAULT_OUTPUT,
    benchmark: str = DEFAULT_BENCHMARK,
    min_rs: float = 0.0,
    show_all: bool = False,
    alert: bool = False,
    bot_token: str = None,
    chat_id: str = None,
):
    """Run the full relative strength scan with dual periods (101 and 123 days)."""

    print("=" * 80)
    print("  RELATIVE STRENGTH SCANNER — Nifty 500 vs Nifty Index (Dual Period)")
    print("=" * 80)
    print(f"  Period 1: {period_1} days | Period 2: {period_2} days | MA: {ma_period} days")
    print(f"  Benchmark: {benchmark}")
    print(f"  Filter: Stock must outperform in BOTH periods")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print()

    # Step 1: Get Nifty 500 symbols
    stocks = fetch_nifty500_symbols()
    yf_symbols = [s["yf_symbol"] for s in stocks]
    symbol_map = {s["yf_symbol"]: s for s in stocks}

    # Step 2: Download all price data (including benchmark)
    # Use the larger period to ensure we have enough data
    max_period = max(period_1, period_2)
    all_symbols = yf_symbols + [benchmark]
    price_data = download_price_data(all_symbols, max_period, ma_period)

    # Check benchmark data
    if benchmark not in price_data:
        print(f"ERROR: Could not get benchmark ({benchmark}) data!")
        sys.exit(1)

    benchmark_prices = price_data[benchmark]

    # Step 3: Calculate RS for each stock (both periods)
    print("\nCalculating relative strength for both periods...")
    results = []

    for yf_sym in yf_symbols:
        if yf_sym not in price_data:
            continue

        # Calculate RS for 101-day period
        rs_data_101 = calculate_relative_strength(
            price_data[yf_sym],
            benchmark_prices,
            period_1,
            ma_period
        )

        # Calculate RS for 123-day period
        rs_data_123 = calculate_relative_strength(
            price_data[yf_sym],
            benchmark_prices,
            period_2,
            ma_period
        )

        # Skip if either calculation failed
        if rs_data_101 is None or rs_data_123 is None:
            continue

        stock_info = symbol_map[yf_sym]

        # Determine signal based on BOTH periods
        signal, combined_trend, detailed_trend = determine_signal(
            rs_data_101["rs_value"],
            rs_data_101["rs_ma"],
            rs_data_123["rs_value"],
            rs_data_123["rs_ma"]
        )

        results.append({
            "symbol": stock_info["symbol"],
            "name": stock_info["name"],
            "close": rs_data_101["close"],
            "rs_value_101": rs_data_101["rs_value"],
            "rs_ma_101": rs_data_101["rs_ma"],
            "rs_value_123": rs_data_123["rs_value"],
            "rs_ma_123": rs_data_123["rs_ma"],
            "signal": signal,
            "rs_trend": combined_trend,
            "trend_detail": detailed_trend,
            "scan_date": rs_data_101["scan_date"]
        })

    if not results:
        print("ERROR: No results calculated. Check data availability.")
        sys.exit(1)

    # Step 4: Sort by average RS value (descending)
    # Average of both periods for ranking
    for r in results:
        r["rs_avg"] = (r["rs_value_101"] + r["rs_value_123"]) / 2

    results.sort(key=lambda x: x["rs_avg"], reverse=True)

    # Step 5: Filter and display
    if not show_all and min_rs > 0:
        results = [r for r in results if r["rs_value_101"] >= min_rs and r["rs_value_123"] >= min_rs]

    display_results = results[:top] if not show_all else results

    # Console output
    print(f"\n{'='*120}")
    print(f"  TOP {len(display_results)} STOCKS BY RELATIVE STRENGTH (Both Periods)")
    print(f"{'='*120}")
    print(f"{'Rank':<5} {'Symbol':<12} {'Close':>8} {'RS-101':>9} {'MA-101':>9} {'RS-123':>9} {'MA-123':>9} {'Signal':<13} {'Trend':<8}")
    print(f"{'-'*120}")

    for i, r in enumerate(display_results, 1):
        print(
            f"{i:<5} {r['symbol']:<12} {r['close']:>8.2f} "
            f"{r['rs_value_101']:>9.4f} {r['rs_ma_101']:>9.4f} "
            f"{r['rs_value_123']:>9.4f} {r['rs_ma_123']:>9.4f} "
            f"{r['signal']:<13} {r['trend_detail']:<8}"
        )

    # Summary stats
    outperformers = [r for r in results if r["signal"] == "OUTPERFORM"]
    neutral = [r for r in results if r["signal"] == "NEUTRAL"]
    underperformers = [r for r in results if r["signal"] == "UNDERPERFORM"]

    print(f"\n{'='*120}")
    print(f"  SUMMARY")
    print(f"{'='*120}")
    print(f"  Total stocks scanned: {len(results)}")
    print(f"  OUTPERFORM (RS>0 & RS>MA in BOTH periods): {len(outperformers)}")
    print(f"  NEUTRAL (RS>0 in both but not outperforming): {len(neutral)}")
    print(f"  UNDERPERFORM (RS<0 in either period):       {len(underperformers)}")
    print(f"{'='*120}")

    # Step 6: Save to CSV
    df = pd.DataFrame(results)
    df.index = range(1, len(df) + 1)
    df.index.name = "rank"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)

    print(f"\n  Results saved to: {output_path.absolute()}")

    # Step 7: Check for new outperformers and send alerts
    if alert:
        check_and_alert(results, bot_token=bot_token, chat_id=chat_id)

    print(f"  Scan complete!\n")

    return results


def setup_cron():
    """Help user set up a daily cron job."""
    script_path = Path(__file__).absolute()

    print("\nTo run this scanner daily at 4:30 PM IST (after market close), add this cron entry:")
    print(f"\n  30 16 * * 1-5 cd {script_path.parent.parent} && python {script_path} --output scans/rs_$(date +\\%Y\\%m\\%d).csv")
    print("\nTo add it automatically, run:")
    print(f"  (crontab -l 2>/dev/null; echo '30 16 * * 1-5 cd {script_path.parent.parent} && python {script_path} --output scans/rs_$(date +\\%Y\\%m\\%d).csv') | crontab -")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Dual-Period Relative Strength Scanner for Nifty 500 stocks vs Nifty Index"
    )
    parser.add_argument("--period-1", type=int, default=DEFAULT_PERIOD_1,
                        help=f"First lookback period in trading days (default: {DEFAULT_PERIOD_1})")
    parser.add_argument("--period-2", type=int, default=DEFAULT_PERIOD_2,
                        help=f"Second lookback period in trading days (default: {DEFAULT_PERIOD_2})")
    parser.add_argument("--ma-period", type=int, default=DEFAULT_MA_PERIOD,
                        help=f"Moving average period for RS (default: {DEFAULT_MA_PERIOD})")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"Number of top outperformers to display (default: {DEFAULT_TOP})")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT,
                        help=f"Output CSV file path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--benchmark", type=str, default=DEFAULT_BENCHMARK,
                        help=f"Benchmark symbol (default: {DEFAULT_BENCHMARK})")
    parser.add_argument("--min-rs", type=float, default=0.0,
                        help="Minimum RS value to include (default: 0.0)")
    parser.add_argument("--show-all", action="store_true",
                        help="Show all stocks, not just top N")
    parser.add_argument("--setup-cron", action="store_true",
                        help="Show cron setup instructions")

    # Telegram alert options
    parser.add_argument("--alert", action="store_true",
                        help="Enable Telegram alerts for new outperformers")
    parser.add_argument("--setup-telegram", action="store_true",
                        help="Configure Telegram bot credentials")
    parser.add_argument("--bot-token", type=str, default=None,
                        help="Telegram bot token (overrides config)")
    parser.add_argument("--chat-id", type=str, default=None,
                        help="Telegram chat ID (overrides config)")

    args = parser.parse_args()

    if args.setup_telegram:
        setup_telegram()
        return

    if args.setup_cron:
        setup_cron()
        return

    run_scan(
        period_1=args.period_1,
        period_2=args.period_2,
        ma_period=args.ma_period,
        top=args.top,
        output=args.output,
        benchmark=args.benchmark,
        min_rs=args.min_rs,
        show_all=args.show_all,
        alert=args.alert,
        bot_token=args.bot_token,
        chat_id=args.chat_id,
    )


if __name__ == "__main__":
    main()
