# Daily Automation Setup

This guide shows how to set up daily automated relative strength scans that run after market close.

## Quick Setup

### Option 1: Using Cron (Recommended)

**Run at 4:30 PM IST (after market close) on weekdays:**

```bash
# Add this line to your crontab
30 16 * * 1-5 /Users/manishkumar/Documents/learning/25-May-2026RelativeStrength/.claude/skills/relative-strength-scanner/scripts/daily_scan.sh >> /tmp/rs_scanner.log 2>&1
```

**To add it automatically:**

```bash
(crontab -l 2>/dev/null; echo "30 16 * * 1-5 /Users/manishkumar/Documents/learning/25-May-2026RelativeStrength/.claude/skills/relative-strength-scanner/scripts/daily_scan.sh >> /tmp/rs_scanner.log 2>&1") | crontab -
```

**To view your current crontab:**

```bash
crontab -l
```

**To edit your crontab manually:**

```bash
crontab -e
```

### Option 2: Using launchd (macOS Native)

Create a launch agent plist file at `~/Library/LaunchAgents/com.rsscanner.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rsscanner.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/manishkumar/Documents/learning/25-May-2026RelativeStrength/.claude/skills/relative-strength-scanner/scripts/daily_scan.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>16</integer>
        <key>Minute</key>
        <integer>30</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/rs_scanner.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/rs_scanner.error.log</string>
</dict>
</plist>
```

**Load the launch agent:**

```bash
launchctl load ~/Library/LaunchAgents/com.rsscanner.daily.plist
```

**Unload (to disable):**

```bash
launchctl unload ~/Library/LaunchAgents/com.rsscanner.daily.plist
```

## What Gets Scanned

The daily scan runs for all four indices:

1. **Nifty 50** - Top 50 large-cap stocks
2. **Nifty 100** - Top 100 stocks
3. **Nifty 200** - Mid to large-cap stocks
4. **Nifty 500** - Comprehensive market coverage

## Output Structure

Results are saved in dated folders:

```
.claude/skills/relative-strength-scanner/scans/
├── 20260526/
│   ├── rs_nifty50.csv
│   ├── rs_nifty100.csv
│   ├── rs_nifty200.csv
│   └── rs_nifty500.csv
├── 20260527/
│   ├── rs_nifty50.csv
│   ...
```

## Default Parameters

- **Period 1**: 103 days
- **Period 2**: 123 days
- **MA Period**: 10 days
- **Filter**: Stocks must outperform in BOTH periods

## Manual Run

To run the daily scan manually:

```bash
cd /Users/manishkumar/Documents/learning/25-May-2026RelativeStrength/.claude/skills/relative-strength-scanner
./scripts/daily_scan.sh
```

## Checking Logs

View the last scan log:

```bash
tail -f /tmp/rs_scanner.log
```

View errors:

```bash
cat /tmp/rs_scanner.error.log
```

## Testing Schedule

To test if your cron job will run:

```bash
# Run the script manually
./scripts/daily_scan.sh

# Check if output files were created
ls -la scans/$(date +%Y%m%d)/
```

## Troubleshooting

### Cron not running?

1. Check if cron is enabled on macOS:
   ```bash
   sudo launchctl list | grep cron
   ```

2. Give Terminal/cron full disk access in System Preferences → Privacy & Security

3. Check cron logs:
   ```bash
   log show --predicate 'process == "cron"' --last 1h
   ```

### Script errors?

1. Check permissions:
   ```bash
   ls -la scripts/daily_scan.sh
   # Should show: -rwxr-xr-x
   ```

2. Test Python path:
   ```bash
   /opt/homebrew/bin/python3 --version
   ```

3. Run manually to see errors:
   ```bash
   ./scripts/daily_scan.sh
   ```

## Customization

Edit `scripts/daily_scan.sh` to:
- Change scan times
- Modify periods (--period-1, --period-2)
- Add/remove indices
- Change output location
- Add Telegram alerts (--alert flag)

## With Telegram Alerts

To receive Telegram notifications for new outperformers, first set up Telegram:

```bash
python3 scripts/relative_strength_scanner.py --setup-telegram
```

Then add the `--alert` flag to the daily scan script.
