# Dual-Period Relative Strength Scanner

A comprehensive Nifty 500 stock scanner that identifies stocks outperforming the Nifty index across **two timeframes simultaneously** (101 days and 123 days) with automated daily scans and Telegram notifications.

## Features

- **Dual-Period Filtering**: Scans for relative strength across both 101-day and 123-day periods
- **Strict Confirmation**: Only flags stocks as OUTPERFORM if they beat Nifty in BOTH periods
- **Automated Daily Scans**: GitHub Actions runs the scanner every weekday after market close
- **Telegram Alerts**: Get notified about:
  - 📈 New stocks entering the OUTPERFORM category
  - 📉 Stocks dropping from OUTPERFORM (potential weakness)
- **Historical Tracking**: CSV results saved as GitHub artifacts (30-day retention)

## Signal Logic

A stock is marked as **OUTPERFORM** only when:
- **101-day period**: RS > 0 AND RS > RS_MA
- **123-day period**: RS > 0 AND RS > RS_MA

This dual-timeframe approach provides stronger confirmation than single-period analysis.

## Setup Instructions

### 1. Fork/Clone this Repository

```bash
git clone https://github.com/manish70158/25-May-2026RelativeStrength.git
cd 25-May-2026RelativeStrength
```

### 2. Set Up Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy the **bot token** (format: `123456:ABC-DEF...`)
4. Start a chat with your new bot
5. Get your **chat ID**:
   - Send any message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find `"chat":{"id": YOUR_CHAT_ID}` in the response

### 3. Configure GitHub Secrets

Go to your repository's Settings → Secrets and variables → Actions → New repository secret

Add two secrets:
- **Name**: `TELEGRAM_BOT_TOKEN`
  **Value**: Your bot token from BotFather

- **Name**: `TELEGRAM_CHAT_ID`
  **Value**: Your chat ID (numeric)

### 4. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Click "I understand my workflows, go ahead and enable them"
3. The workflow will run automatically every weekday at 4:30 PM IST (11:00 AM UTC)

### 5. Manual Trigger (Optional)

To run the scan immediately:
1. Go to **Actions** → **Daily Relative Strength Scan**
2. Click "Run workflow" → "Run workflow"

## Local Usage

### Installation

```bash
cd .claude/skills/relative-strength-scanner/scripts
pip install -r requirements.txt
```

### Run Scanner Locally

```bash
# Basic scan
python relative_strength_scanner.py

# With Telegram alerts
python relative_strength_scanner.py --alert

# Custom periods (if you want to override defaults)
python relative_strength_scanner.py --period-1 101 --period-2 123

# Show all stocks (not just top 20)
python relative_strength_scanner.py --show-all
```

### Configure Telegram (Local)

```bash
python relative_strength_scanner.py --setup-telegram
```

This saves your credentials to `config.json` for local runs.

## GitHub Action Details

### Schedule
- **Runs**: Every weekday at 11:00 AM UTC (4:30 PM IST)
- **Markets**: After Indian market close at 3:30 PM IST

### Workflow Steps
1. Checkout repository
2. Install Python dependencies
3. Run RS scanner with `--alert` flag
4. Upload CSV results as artifact
5. Optionally commit results back to repo

### Output Artifacts
- CSV files saved in `scans/` directory
- Format: `rs_YYYYMMDD.csv`
- Retained for 30 days

## Understanding the Output

### Console Output

```
Rank  Symbol        Close   RS-101     MA-101     RS-123     MA-123     Signal         Trend
----  ------------  ------  ---------  ---------  ---------  ---------  -------------  --------
1     ZOMATO        145.23   0.1234     0.1100     0.1456     0.1320    OUTPERFORM     UP/UP
2     ADANIPORTS    850.45   0.0987     0.0890     0.1123     0.1050    OUTPERFORM     UP/UP
```

### Telegram Alert

```
📊 RS Scanner Update (2026-05-25)
========================================

✅ NEW OUTPERFORMERS (12)
Stocks newly beating Nifty in BOTH periods

1. ZOMATO | 101d: +12.3% | 123d: +14.6%
2. ADANIPORTS | 101d: +9.9% | 123d: +11.2%
...

----------------------------------------

⚠️ DROPPED FROM OUTPERFORM (5)
No longer beating Nifty in both periods

1. INFY
2. TCS
...
```

## CSV Columns

- `symbol`: NSE trading symbol
- `name`: Company name
- `close`: Latest closing price
- `rs_value_101`: Relative strength (101-day period)
- `rs_ma_101`: RS moving average (101-day)
- `rs_value_123`: Relative strength (123-day period)
- `rs_ma_123`: RS moving average (123-day)
- `rs_avg`: Average RS across both periods (for ranking)
- `signal`: OUTPERFORM / NEUTRAL / UNDERPERFORM
- `rs_trend`: UP / DOWN / MIXED
- `trend_detail`: Individual trends (e.g., "UP/UP")
- `scan_date`: Date of scan

## Interpreting Results

### Strong Candidates (Best)
- **Signal**: OUTPERFORM
- **Trend**: UP/UP
- Both RS values positive and above their MAs
- Confirmed momentum across multiple timeframes

### Watch List
- **Signal**: NEUTRAL
- RS positive in both periods but may be losing momentum in one

### Avoid
- **Signal**: UNDERPERFORM
- RS negative in either period
- Lagging behind Nifty

## Troubleshooting

### GitHub Action Not Running
- Check if Actions are enabled in your repository
- Verify the workflow file exists at `.github/workflows/daily-rs-scan.yml`
- Check Actions tab for error logs

### No Telegram Alerts
- Verify secrets are set correctly in repository settings
- Test your bot token: `https://api.telegram.org/bot<TOKEN>/getMe`
- Make sure you've sent at least one message to your bot

### Script Errors
- Ensure Python 3.11+ is installed
- Install dependencies: `pip install -r requirements.txt`
- Check for internet connectivity (script downloads stock data)

## Technical Details

### Data Source
- Stock prices: Yahoo Finance API (via `yfinance`)
- Nifty 500 list: NSE India (cached for 7 days)
- Benchmark: ^NSEI (Nifty 50 Index)

### Calculation Method
```python
RS = (Stock_Today / Stock_N_ago) / (Nifty_Today / Nifty_N_ago) - 1
RS_MA = SMA(RS, 10)
```

### Storage
- `nifty500_symbols.json`: Cached stock list
- `previous_outperformers.json`: Previous scan state (for alert diffing)
- `config.json`: Telegram credentials (local only)

## License

MIT License - Feel free to modify and distribute

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions, please open a GitHub issue.
