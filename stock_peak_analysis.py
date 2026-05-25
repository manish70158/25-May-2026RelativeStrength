#!/usr/bin/env python3
"""
Stock Peak & Low Analyzer
Identifies peaks and lows in stock price movements and finds reasons for them.

Usage:
    python stock_peak_analysis.py RELIANCE
    python stock_peak_analysis.py HDFCBANK --threshold 15 --days 365
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import numpy as np


class StockPeakAnalyzer:
    """Analyzes stock peaks and lows and generates reports."""

    def __init__(self, symbol: str, threshold_pct: float = 20.0, days: int = 365):
        """
        Initialize analyzer.

        Args:
            symbol: Stock symbol (e.g., RELIANCE, HDFCBANK)
            threshold_pct: Percentage threshold for peak/low detection (default: 20%)
            days: Number of days to analyze (default: 365)
        """
        self.symbol = symbol.upper()
        self.yf_symbol = f"{self.symbol}.NS"
        self.threshold = threshold_pct / 100.0
        self.days = days
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=days)

        # Data containers
        self.price_data = None
        self.nifty_data = None
        self.peaks = []
        self.lows = []

    def fetch_price_data(self):
        """Fetch historical price data from Yahoo Finance."""
        print(f"Fetching price data for {self.symbol}...")

        try:
            # Fetch stock data
            stock = yf.Ticker(self.yf_symbol)
            self.price_data = stock.history(
                start=self.start_date.strftime("%Y-%m-%d"),
                end=self.end_date.strftime("%Y-%m-%d")
            )

            if self.price_data.empty:
                raise ValueError(f"No data found for {self.symbol}")

            # Fetch Nifty data for comparison
            nifty = yf.Ticker("^NSEI")
            self.nifty_data = nifty.history(
                start=self.start_date.strftime("%Y-%m-%d"),
                end=self.end_date.strftime("%Y-%m-%d")
            )

            print(f"  ✓ Fetched {len(self.price_data)} days of data")
            return True

        except Exception as e:
            print(f"  ✗ Error fetching data: {e}")
            return False

    def identify_peaks_and_lows(self):
        """Identify significant peaks and lows based on percentage threshold."""
        print(f"\nIdentifying peaks and lows (threshold: {self.threshold*100:.1f}%)...")

        closes = self.price_data['Close'].values
        dates = self.price_data.index

        # Find local extrema
        peaks_idx = []
        lows_idx = []

        window = 10  # Look at 10-day windows for local extrema

        for i in range(window, len(closes) - window):
            # Check if it's a local maximum
            if closes[i] == max(closes[i-window:i+window+1]):
                # Check if it's significant (>threshold from recent low)
                recent_low = min(closes[max(0, i-30):i])
                if recent_low > 0:
                    change = (closes[i] - recent_low) / recent_low
                    if change >= self.threshold:
                        peaks_idx.append(i)

            # Check if it's a local minimum
            if closes[i] == min(closes[i-window:i+window+1]):
                # Check if it's significant (>threshold from recent high)
                recent_high = max(closes[max(0, i-30):i])
                if recent_high > 0:
                    change = (recent_high - closes[i]) / recent_high
                    if change >= self.threshold:
                        lows_idx.append(i)

        # Build peak/low records
        for idx in peaks_idx:
            self.peaks.append({
                'date': dates[idx],
                'price': closes[idx],
                'type': 'PEAK',
                'change_pct': self._calc_change_from_reference(idx, closes, 'peak')
            })

        for idx in lows_idx:
            self.lows.append({
                'date': dates[idx],
                'price': closes[idx],
                'type': 'LOW',
                'change_pct': self._calc_change_from_reference(idx, closes, 'low')
            })

        print(f"  ✓ Found {len(self.peaks)} peaks and {len(self.lows)} lows")
        return self.peaks + self.lows

    def _calc_change_from_reference(self, idx: int, closes: np.ndarray, event_type: str) -> float:
        """Calculate percentage change from reference point."""
        lookback = 30
        start_idx = max(0, idx - lookback)

        if event_type == 'peak':
            reference = min(closes[start_idx:idx+1]) if idx > start_idx else closes[idx]
            if reference > 0:
                return ((closes[idx] - reference) / reference) * 100
        else:  # low
            reference = max(closes[start_idx:idx+1]) if idx > start_idx else closes[idx]
            if reference > 0:
                return ((reference - closes[idx]) / reference) * 100

        return 0.0

    def find_reasons(self, events: list) -> list:
        """Find reasons for each peak/low event."""
        print("\nFinding reasons for peaks and lows...")

        enriched_events = []

        for event in events:
            event_date = event['date']
            print(f"  Analyzing {event['type']} on {event_date.strftime('%Y-%m-%d')}...")

            reasons = []

            # 1. Check Nifty movement (sector/market trend)
            nifty_change = self._get_nifty_movement(event_date)
            if nifty_change:
                reasons.append(nifty_change)

            # 2. Scrape news from screener.in
            news = self._scrape_screener_news(event_date)
            if news:
                reasons.extend(news)

            # 3. Check for quarterly results
            result_info = self._check_quarterly_results(event_date)
            if result_info:
                reasons.append(result_info)

            # 4. Check corporate actions
            corp_actions = self._check_corporate_actions(event_date)
            if corp_actions:
                reasons.extend(corp_actions)

            # Add reasons to event
            event['reasons'] = reasons
            event['reason_summary'] = "; ".join(reasons) if reasons else "No specific reason identified"
            enriched_events.append(event)

        print(f"  ✓ Analysis complete")
        return enriched_events

    def _get_nifty_movement(self, event_date) -> str:
        """Check Nifty index movement around the event date."""
        try:
            # Get Nifty price on event date and 5 days before
            event_idx = self.nifty_data.index.get_indexer([event_date], method='nearest')[0]

            if event_idx < 5:
                return None

            nifty_before = self.nifty_data['Close'].iloc[event_idx - 5]
            nifty_event = self.nifty_data['Close'].iloc[event_idx]

            if nifty_before > 0:
                nifty_change = ((nifty_event - nifty_before) / nifty_before) * 100

                if abs(nifty_change) > 3:
                    direction = "rallied" if nifty_change > 0 else "fell"
                    return f"Market {direction} {abs(nifty_change):.1f}% (Nifty correlation)"

        except Exception as e:
            pass

        return None

    def _scrape_screener_news(self, event_date) -> list:
        """Scrape news from screener.in around the event date."""
        news_items = []

        try:
            # Screener.in company page URL
            url = f"https://www.screener.in/company/{self.symbol}/consolidated/"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find announcements section
                announcements = soup.find_all('li', class_='announcement')

                for announcement in announcements[:20]:  # Check recent 20 announcements
                    try:
                        date_elem = announcement.find('span', class_='announcement-date')
                        text_elem = announcement.find('span', class_='announcement-text')

                        if date_elem and text_elem:
                            ann_date_str = date_elem.text.strip()
                            ann_text = text_elem.text.strip()

                            # Parse date (format: "Dec 2023" or "15 Dec 2023")
                            ann_date = self._parse_announcement_date(ann_date_str)

                            if ann_date:
                                # Check if within 7 days of event
                                days_diff = abs((event_date - ann_date).days)

                                if days_diff <= 7:
                                    news_items.append(f"News: {ann_text[:100]}")

                    except Exception:
                        continue

        except Exception as e:
            print(f"    ⚠ Could not fetch screener.in news: {e}")

        return news_items[:3]  # Return top 3 news items

    def _parse_announcement_date(self, date_str: str):
        """Parse announcement date from various formats."""
        try:
            # Try common formats
            for fmt in ["%d %b %Y", "%b %Y", "%d %B %Y", "%B %Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except:
                    continue
        except:
            pass

        return None

    def _check_quarterly_results(self, event_date) -> str:
        """Check if quarterly results were announced near the event date."""
        # Typical result months: Jan, Apr, Jul, Oct (for Q3, Q4, Q1, Q2)
        result_months = [1, 4, 7, 10]
        event_month = event_date.month

        # Check if within 15 days of typical result period
        for result_month in result_months:
            if abs(event_month - result_month) <= 1:
                quarter_map = {1: "Q3", 4: "Q4", 7: "Q1", 10: "Q2"}
                quarter = quarter_map.get(result_month)
                return f"Quarterly results period ({quarter} typically announced)"

        return None

    def _check_corporate_actions(self, event_date) -> list:
        """Check for corporate actions like splits, dividends, bonuses."""
        actions = []

        try:
            stock = yf.Ticker(self.yf_symbol)

            # Check dividends
            dividends = stock.dividends
            if not dividends.empty:
                for div_date, div_amount in dividends.items():
                    if abs((event_date - div_date).days) <= 10:
                        actions.append(f"Dividend announced: ₹{div_amount:.2f}")

            # Check splits
            splits = stock.splits
            if not splits.empty:
                for split_date, split_ratio in splits.items():
                    if abs((event_date - split_date).days) <= 10:
                        actions.append(f"Stock split: {split_ratio}")

        except Exception:
            pass

        return actions

    def generate_csv_report(self, events: list):
        """Generate CSV report of peaks and lows with reasons."""
        if not events:
            print("\n⚠ No peaks or lows found. Adjust threshold or time period.")
            return None

        # Prepare data for CSV
        report_data = []

        for event in events:
            report_data.append({
                'Date': event['date'].strftime('%Y-%m-%d'),
                'Type': event['type'],
                'Price': f"₹{event['price']:.2f}",
                'Change %': f"{event['change_pct']:.2f}%",
                'Reasons': event['reason_summary']
            })

        # Create DataFrame
        df = pd.DataFrame(report_data)

        # Sort by date
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.symbol}_peak_low_analysis_{timestamp}.csv"

        # Save to CSV
        output_dir = Path("reports")
        output_dir.mkdir(exist_ok=True)

        filepath = output_dir / filename
        df.to_csv(filepath, index=False)

        print(f"\n✅ Report generated: {filepath}")
        print(f"\nSummary:")
        print(f"  Peaks: {len([e for e in events if e['type'] == 'PEAK'])}")
        print(f"  Lows: {len([e for e in events if e['type'] == 'LOW'])}")
        print(f"  Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")

        # Display preview
        print(f"\nPreview:")
        print(df.to_string(index=False))

        return filepath

    def run(self):
        """Run the complete analysis pipeline."""
        print(f"\n{'='*70}")
        print(f"  Stock Peak & Low Analyzer: {self.symbol}")
        print(f"{'='*70}")

        # Step 1: Fetch data
        if not self.fetch_price_data():
            return False

        # Step 2: Identify peaks and lows
        events = self.identify_peaks_and_lows()

        if not events:
            print("\n⚠ No significant peaks or lows found. Try adjusting the threshold.")
            return False

        # Step 3: Find reasons
        enriched_events = self.find_reasons(events)

        # Step 4: Generate report
        self.generate_csv_report(enriched_events)

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze stock peaks and lows with reason detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stock_peak_analysis.py RELIANCE
  python stock_peak_analysis.py HDFCBANK --threshold 15
  python stock_peak_analysis.py TCS --days 730 --threshold 25
        """
    )

    parser.add_argument(
        'symbol',
        type=str,
        help='Stock symbol (e.g., RELIANCE, HDFCBANK, TCS)'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=20.0,
        help='Percentage threshold for peak/low detection (default: 20%%)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days to analyze (default: 365)'
    )

    args = parser.parse_args()

    # Create analyzer and run
    analyzer = StockPeakAnalyzer(
        symbol=args.symbol,
        threshold_pct=args.threshold,
        days=args.days
    )

    success = analyzer.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
