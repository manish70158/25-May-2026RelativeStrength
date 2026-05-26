# GitHub Actions Daily Automation

The repository now has a GitHub Actions workflow that automatically runs the daily relative strength scans.

## How It Works

The workflow (`.github/workflows/daily_scan.yml`) runs:
- **Automatically**: Every weekday at 4:30 PM IST (11:00 AM UTC)
- **Manually**: You can trigger it anytime from the GitHub Actions tab

It performs:
1. Scans all four indices (Nifty 50, 100, 200, 500)
2. Saves results to dated folders (e.g., `scans/20260526/`)
3. Commits and pushes results back to the repository
4. Sends Telegram alerts (if configured)

## Setup Instructions

### 1. Push the Workflow File

First, commit and push the workflow file to GitHub:

```bash
git add .github/workflows/daily_scan.yml
git commit -m "Add GitHub Actions workflow for daily scans"
git push
```

### 2. Configure Telegram Alerts (Optional)

To receive Telegram notifications when scans complete:

#### Step 1: Create a Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save the **bot token** you receive (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Step 2: Get Your Chat ID
1. Start a chat with your bot
2. Send any message to it
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your **chat ID** in the response (looks like `123456789`)

#### Step 3: Add Secrets to GitHub
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these two secrets:

**Secret 1:**
- Name: `TELEGRAM_BOT_TOKEN`
- Value: Your bot token from BotFather

**Secret 2:**
- Name: `TELEGRAM_CHAT_ID`
- Value: Your chat ID

### 3. Verify Setup

#### Check Workflow Status
1. Go to the **Actions** tab in your GitHub repository
2. You should see "Daily Relative Strength Scan" workflow
3. Green checkmark = successful run
4. Red X = failed run (click to see logs)

#### Manual Test Run
1. Go to **Actions** → **Daily Relative Strength Scan**
2. Click **Run workflow** dropdown
3. Click green **Run workflow** button
4. Wait for completion (~5-10 minutes)
5. Check the **scans/** folder for new results

## Schedule

The workflow runs at:
- **4:30 PM IST** (after market close)
- **Monday through Friday** only
- Automatically commits results

## Output

Each run creates a dated folder structure:

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

## Troubleshooting

### Workflow Not Running

**Check these:**
1. Is the workflow file pushed to GitHub? (Check `.github/workflows/` folder)
2. Is it enabled? Go to Actions → Workflows → Check if disabled
3. Is the repository active? (GitHub disables workflows in inactive repos after 60 days)
4. Check workflow logs for errors

### No Telegram Alerts

**Check these:**
1. Are secrets configured? (Settings → Secrets and variables → Actions)
2. Are secret names exactly `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`?
3. Did you send a message to the bot first?
4. Check workflow logs for Telegram-related errors

### Scan Errors

**Check these:**
1. Look at the workflow run logs (Actions → Click failed run → Click job)
2. Common issues:
   - Network timeout (Yahoo Finance throttling)
   - Invalid symbols in index lists
   - Python dependency issues

### Force Run Today

If you want to run immediately (don't wait for 4:30 PM):

```bash
# Go to GitHub → Actions → Daily Relative Strength Scan → Run workflow
```

Or locally:
```bash
cd .claude/skills/relative-strength-scanner
./scripts/daily_scan.sh
```

## Monitoring

### Daily Check
Every day after 5:00 PM IST:
1. Go to GitHub Actions tab
2. Verify today's run completed successfully
3. Check the scans folder for new results

### Weekly Review
Every week:
1. Review the scans across multiple days
2. Track which stocks consistently appear as OUTPERFORMERS
3. Analyze Telegram alerts for emerging trends

## Disabling Automation

If you want to temporarily disable:

1. **GitHub Actions**: Go to Actions → Workflows → Daily Relative Strength Scan → Disable workflow
2. **Local Cron**: Run `crontab -e` and comment out the line with `#`

## Cost

GitHub Actions is **FREE** for public repositories and includes:
- 2,000 minutes/month for private repos
- Unlimited for public repos

This workflow uses ~5-10 minutes per run, well within free limits.

## Next Steps

1. ✅ Push the workflow file to GitHub
2. ⬜ Add Telegram secrets (optional)
3. ⬜ Trigger a manual test run
4. ⬜ Verify results are committed
5. ⬜ Wait for automatic run tomorrow at 4:30 PM IST
