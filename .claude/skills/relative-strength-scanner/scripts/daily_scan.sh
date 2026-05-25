#!/bin/bash
# Daily Relative Strength Scanner
# Runs after market close and generates dated CSV files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE_SUFFIX=$(date +%Y%m%d)
OUTPUT_DIR="$SCRIPT_DIR/../scans/$DATE_SUFFIX"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Daily RS Scan - $(date '+%Y-%m-%d %H:%M')"
echo "=========================================="

# Run scans for all indices
echo "Scanning Nifty 50..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/relative_strength_scanner.py" \
    --index nifty50 \
    --period-1 103 \
    --period-2 123 \
    --output "$OUTPUT_DIR/rs_nifty50.csv"

echo ""
echo "Scanning Nifty 100..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/relative_strength_scanner.py" \
    --index nifty100 \
    --period-1 103 \
    --period-2 123 \
    --output "$OUTPUT_DIR/rs_nifty100.csv"

echo ""
echo "Scanning Nifty 200..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/relative_strength_scanner.py" \
    --index nifty200 \
    --period-1 103 \
    --period-2 123 \
    --output "$OUTPUT_DIR/rs_nifty200.csv"

echo ""
echo "Scanning Nifty 500..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/relative_strength_scanner.py" \
    --index nifty500 \
    --period-1 103 \
    --period-2 123 \
    --output "$OUTPUT_DIR/rs_nifty500.csv"

echo ""
echo "=========================================="
echo "All scans complete!"
echo "Results saved to: $OUTPUT_DIR"
echo "=========================================="
