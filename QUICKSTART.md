# Quick Start Guide - Tradier Integration

## Prerequisites

Your Tradier API credentials are already configured in `config.yaml`:
- API Token: `YapJSqXqDZ5ui8HtoP7QEyIX7CIk`
- Account: `VA31706838`
- Environment: Sandbox

## ⚠️ Important: Run on Your MacBook

The Tradier API requires **IP whitelisting**. Since your MacBook curl test succeeded, run the scanner there:

```bash
cd /path/to/sec
git pull origin claude/ibkr-whale-options-scanner-011CUfbknnpPBbzSGZS9Haic
```

## Option 1: CLI Scanner (Command Line)

### Start the scanner:
```bash
python scanner.py
```

**What it does:**
- Scans your watchlist symbols (SPY, QQQ, AAPL, etc.)
- Applies whale detection filters
- Shows signals in the terminal
- Runs continuously (scans every 60 seconds)

**Expected output:**
```
Initializing Whale Scanner...
Data provider: TRADIER
✓ Using Tradier API (no TWS required!)
✓ Initialized with watchlist: SPY, QQQ, AAPL, NVDA, TSLA, AMD, MSFT, GOOGL, META, AMZN

Scanning SPY...
SPY current price: $XXX.XX
✓ Fetched XXX option contracts for SPY
P/C Ratio: X.XXX
[Signals and whale activity will be shown here]
```

### Stop the scanner:
Press `Ctrl+C`

---

## Option 2: Web UI (Recommended)

### Start the web application:
```bash
python web_app.py
```

**Expected output:**
```
 * Running on http://0.0.0.0:8080
 * Running on http://127.0.0.1:8080
Press CTRL+C to quit
```

### Access the dashboard:
1. Open your browser
2. Go to: **http://localhost:8080**
3. You'll see the Whale Scanner Dashboard

### Using the Web UI:

**Dashboard Features:**
- 📊 Real-time signal display
- 📈 P/C ratio charts
- 🎯 Whale combo signals (Strong Bull, Institutional Hedge, etc.)
- 📋 Watchlist management
- ⚙️ Configuration editor

**Start Scanning:**
1. Click **"Start Scanner"** button
2. Scanner will connect to Tradier API
3. Watch signals appear in real-time
4. Signals update every 60 seconds

**Stop Scanning:**
- Click **"Stop Scanner"** button

---

## Verify Tradier is Being Used

When you start either the CLI or Web UI, look for this message:
```
Data provider: TRADIER
✓ Using Tradier API (no TWS required!)
```

If you see this, you're successfully using Tradier! 🎉

---

## Test First (Recommended)

Before running the full scanner, test the integration:

```bash
python test_tradier_integration.py
```

This will verify:
- ✅ API connection works
- ✅ Options data can be fetched
- ✅ P/C ratios calculate correctly

---

## Configuration

The scanner is already configured to use Tradier in `config.yaml`:

```yaml
data_source:
  provider: "tradier"  # ← Currently using Tradier

tradier:
  api_token: "YapJSqXqDZ5ui8HtoP7QEyIX7CIk"
  sandbox: true
  account_id: "VA31706838"
```

### To Switch Back to IBKR:
Edit `config.yaml` and change:
```yaml
data_source:
  provider: "ibkr"  # Switch to IBKR TWS
```

---

## Watchlist Symbols

Default watchlist (edit in `config.yaml`):
- SPY - S&P 500 ETF
- QQQ - Nasdaq ETF
- AAPL - Apple
- NVDA - Nvidia
- TSLA - Tesla
- AMD - AMD
- MSFT - Microsoft
- GOOGL - Google
- META - Meta
- AMZN - Amazon

### To modify watchlist:
Edit `config.yaml` under `watchlist: symbols:`

---

## Troubleshooting

### Error: "Access denied" (403)
**Problem:** Your IP is not whitelisted in Tradier

**Solution:**
1. Make sure you're running on your MacBook (not the server)
2. Or whitelist the server IP in Tradier dashboard

### Error: "No options data"
**Problem:** Market might be closed

**Solution:**
- Run during market hours (9:30 AM - 4:00 PM ET)
- Or wait for next trading day

### Error: "Module not found"
**Problem:** Missing dependencies

**Solution:**
```bash
pip install -r requirements.txt
```

### Web UI not loading
**Problem:** Port 8080 might be in use

**Solution:**
```bash
# Check what's using port 8080
lsof -i :8080

# Kill the process if needed
kill <PID>

# Or change port in web_app.py (line 445)
```

---

## Quick Commands Cheat Sheet

```bash
# Pull latest code
git pull origin claude/ibkr-whale-options-scanner-011CUfbknnpPBbzSGZS9Haic

# Test integration
python test_tradier_integration.py

# Start CLI scanner
python scanner.py

# Start Web UI
python web_app.py

# View logs
tail -f logs/whale_scanner.log

# Check config
cat config.yaml | grep -A 3 "data_source"
```

---

## What Happens When Scanner Runs

1. **Connection:** Connects to Tradier API (no TWS needed!)
2. **Data Fetch:** Downloads options chains for each symbol
3. **Filtering:** Applies whale filters:
   - Liquidity Gate (Volume > 500K, OI > 100K)
   - Anomaly Gate (P/C ratio deviations)
   - Conviction Gate (Volume vs OI analysis)
   - Volatility Gate (IV rank extremes)
4. **Signal Detection:** Identifies whale combo signals:
   - 🐂 Strong Bull (P/C < 0.7, high call volume)
   - 🛡️ Institutional Hedge (P/C > 1.3, put protection)
   - 🤪 Retail FOMO (P/C < 0.3, extreme speculation)
5. **Alerts:** Displays signals in terminal or web dashboard

---

## Performance Notes

- **Scan Interval:** 60 seconds (configurable in `config.yaml`)
- **Data Delay:** 15 minutes (Tradier free tier)
- **Symbols:** 10 in default watchlist
- **Expected Scan Time:** ~5-10 seconds per symbol

---

## Need Help?

- **Full Setup Guide:** See `TRADIER_SETUP.md`
- **Logs:** Check `logs/whale_scanner.log`
- **Debug Mode:** Set `logging: level: DEBUG` in `config.yaml`

Happy whale hunting! 🐋📈
