# Stock Peak & Low Analyzer

A Python script that identifies significant peaks and lows in stock prices and finds reasons for these movements.

## Features

- 📈 **Peak Detection**: Identifies significant price peaks based on percentage threshold
- 📉 **Low Detection**: Identifies significant price lows based on percentage threshold
- 🔍 **Reason Analysis**: Finds reasons for each peak/low:
  - Market correlation (Nifty index movements)
  - News from screener.in
  - Quarterly results announcements
  - Corporate actions (dividends, splits, bonuses)
- 📊 **CSV Reports**: Generates detailed CSV reports for each analysis

## Installation

```bash
# Install dependencies
pip install -r requirements_peak_analysis.txt

# Or install individually
pip install pandas yfinance beautifulsoup4 requests numpy lxml
```

## Usage

### Basic Usage

```bash
# Analyze HDFC Bank for last 1 year (default threshold: 20%)
python stock_peak_analysis.py HDFCBANK

# Analyze Reliance with custom threshold
python stock_peak_analysis.py RELIANCE --threshold 15

# Analyze TCS for last 2 years with 25% threshold
python stock_peak_analysis.py TCS --days 730 --threshold 25
```

### Command-Line Options

```
positional arguments:
  symbol               Stock symbol (e.g., RELIANCE, HDFCBANK, TCS)

options:
  --threshold FLOAT    Percentage threshold for peak/low detection (default: 20%)
  --days INT          Number of days to analyze (default: 365)
  --help              Show help message
```

## How It Works

### 1. Peak/Low Detection

The script uses a percentage-based algorithm:

- **Local Extrema**: Finds local maxima and minima in a 10-day window
- **Significance Filter**: Only flags peaks/lows that represent >threshold% change from recent reference points
- **Reference Points**:
  - For peaks: Recent 30-day low
  - For lows: Recent 30-day high

### 2. Reason Detection

For each identified peak/low, the script analyzes:

#### Market Correlation
- Compares stock movement with Nifty 50 index
- Flags significant market moves (>3%) during the same period

#### News from Screener.in
- Scrapes recent announcements from the stock's screener.in page
- Identifies news within 7 days of the peak/low event

#### Quarterly Results
- Checks if the event occurred during typical quarterly result periods
- Q1 (July), Q2 (October), Q3 (January), Q4 (April)

#### Corporate Actions
- Uses Yahoo Finance data to identify:
  - Dividend announcements
  - Stock splits
  - Bonus issues
- Flags actions within 10 days of the event

## Output

### CSV Report

Generated in `reports/` directory with filename format:
```
{SYMBOL}_peak_low_analysis_{TIMESTAMP}.csv
```

**Columns:**
- **Date**: Date of peak/low
- **Type**: PEAK or LOW
- **Price**: Stock price at that point
- **Change %**: Percentage change from reference point
- **Reasons**: Comma-separated list of identified reasons

### Example Output

```
Date        Type   Price     Change %   Reasons
2026-03-30  LOW    ₹731.55   20.98%     Market fell 3.4% (Nifty correlation); Quarterly results period (Q4 typically announced)
2025-12-15  PEAK   ₹920.30   22.45%     News: Strong Q3 results announced; Market rallied 4.2% (Nifty correlation)
```

## Examples

### Example 1: Recent Peak in Tech Stock

```bash
$ python stock_peak_analysis.py TCS --threshold 18

======================================================================
  Stock Peak & Low Analyzer: TCS
======================================================================
Fetching price data for TCS...
  ✓ Fetched 249 days of data

Identifying peaks and lows (threshold: 18.0%)...
  ✓ Found 2 peaks and 1 lows

Finding reasons for peaks and lows...
  Analyzing PEAK on 2026-02-15...
  Analyzing LOW on 2026-04-10...
  Analyzing PEAK on 2025-11-20...
  ✓ Analysis complete

✅ Report generated: reports/TCS_peak_low_analysis_20260526_010203.csv
```

### Example 2: Banking Sector Analysis

```bash
$ python stock_peak_analysis.py HDFCBANK --threshold 15 --days 730

# Analyzes 2 years of HDFC Bank data with 15% threshold
# Captures both bull and bear market movements
```

### Example 3: Volatile Small-Cap

```bash
$ python stock_peak_analysis.py SUZLON --threshold 30

# Higher threshold for volatile stocks
# Filters out minor fluctuations
```

## Tips for Best Results

### Choosing the Right Threshold

- **Large-cap stocks** (RELIANCE, TCS, HDFC): 15-20%
- **Mid-cap stocks**: 20-25%
- **Small-cap/volatile stocks**: 25-35%

If you get too many peaks/lows, increase the threshold.
If you get too few, decrease the threshold.

### Time Period Selection

- **Last 1 year** (365 days): Good for recent trend analysis
- **Last 2 years** (730 days): Captures full market cycles
- **Custom period**: Use `--days` for specific analysis needs

### Interpreting Results

**Strong Signals:**
- Peak/low with multiple reasons (market + news + results)
- High percentage change (>25%)
- Clear corporate action trigger

**Weak Signals:**
- Only "Quarterly results period" reason (may be coincidental)
- Low percentage change near threshold
- No specific news or events

## Troubleshooting

### No Peaks or Lows Found

```
⚠ No significant peaks or lows found. Try adjusting the threshold.
```

**Solutions:**
- Lower the `--threshold` parameter
- Increase the `--days` to analyze a longer period
- Check if the stock symbol is correct (use NSE symbols)

### Data Fetch Errors

```
✗ Error fetching data: No data found for SYMBOL
```

**Solutions:**
- Verify the stock symbol (must be NSE listed)
- Check internet connection
- Try adding `.NS` suffix manually in the code if needed

### Screener.in Scraping Issues

```
⚠ Could not fetch screener.in news: ...
```

**Note:** This is non-critical. The script will continue with other reason detection methods.

## Data Sources

- **Price Data**: Yahoo Finance (`yfinance` library)
- **News**: Screener.in (web scraping)
- **Corporate Actions**: Yahoo Finance
- **Market Data**: Nifty 50 index from Yahoo Finance

## Limitations

1. **News Coverage**: Limited to announcements available on screener.in
2. **Historical News**: Older news may not be available
3. **Data Accuracy**: Depends on Yahoo Finance data quality
4. **Rate Limiting**: Excessive scraping may be rate-limited

## Future Enhancements

Potential additions:
- [ ] Technical indicators (RSI, MACD) for confirmation
- [ ] Sentiment analysis from news headlines
- [ ] Sector comparison analysis
- [ ] Chart generation with annotated peaks/lows
- [ ] Multiple stock batch processing
- [ ] Email/Telegram alerts for new peaks/lows

## Contributing

To add new reason detection methods:

1. Add method to `StockPeakAnalyzer` class
2. Call it in `find_reasons()` method
3. Ensure it returns a list of reason strings

Example:
```python
def _check_new_reason(self, event_date) -> list:
    reasons = []
    # Your detection logic here
    return reasons
```

## License

MIT License - Free to use and modify

## Support

For issues or questions, open a GitHub issue at:
https://github.com/manish70158/25-May-2026RelativeStrength/issues

---

**Created**: 2026-05-26
**Version**: 1.0.0
**Author**: Generated for Nifty 500 RS Scanner Project
