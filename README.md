# 🐋 IBKR Whale Options Scanner

**Professional-grade options flow scanner for detecting institutional whale activity using IBKR TWS/Gateway API**

Monitor unusual options activity, track put/call ratios, open interest changes, volume anomalies, and IV rank to identify where smart money is positioned.

## 🌐 Two Ways to Use

### 1. **Web UI (Recommended)** 🖥️
Beautiful, interactive dashboard with real-time updates, charts, and easy controls.
```bash
./start_web.sh
# Open http://localhost:5000 in your browser
```

### 2. **Command Line** ⌨️
Traditional CLI for scripting and automation.
```bash
python scanner.py --mode continuous
```

**See [WEB_UI_README.md](WEB_UI_README.md) for complete Web UI guide.**

---

## 🎯 Features

### Core Whale Detection Filters

1. **Liquidity Gate** - Filter for liquid contracts
   - Volume > 500K contracts
   - Open Interest > 100K per expiry
   - Minimum OI per strike: 5,000

2. **Anomaly Gate** - P/C Ratio Analysis
   - Track deviation from 10/20-day averages
   - Detect extreme bullish (<0.7) or bearish (>1.3) sentiment
   - Flag whale activity (P/C ≤ 0.3)

3. **Conviction Gate** - Volume vs Open Interest
   - Volume > 2x average daily volume
   - Today's volume > 3x last 10-day average
   - OI change > 25K = conviction trade
   - High volume + no OI change = noise/day trading

4. **Volatility Gate** - IV Rank Extremes
   - IVR > 80 = Expensive volatility (sell premium)
   - IVR < 20 = Cheap volatility (buy options)
   - Detect IV term structure inversions

### Whale Combo Signals (High Conviction)

- **Strong Bull**: Low P/C + High Call Volume + Rising Call OI + Low IVR
- **Institutional Hedge**: High P/C + Put Volume Spike + Rising Put OI + High IVR
- **Retail FOMO**: Extreme Low P/C + High Volume + No OI Change (FADE signal)

### Advanced Analytics

- Volume/OI divergence detection
- Skew analysis (Put IV vs Call IV)
- IV term structure monitoring
- Historical comparison (10-day & 20-day averages)
- Statistical deviation tracking (σ-based anomalies)

---

## 📋 Requirements

### Software Requirements

1. **Interactive Brokers Account**
   - Paper trading or live account
   - Market data subscriptions for options

2. **IBKR Trader Workstation (TWS) or IB Gateway**
   - Download from [Interactive Brokers](https://www.interactivebrokers.com/en/index.php?f=16040)
   - Enable API connections

3. **Python 3.8+**

### IBKR Setup

1. **Install TWS or IB Gateway**
   ```bash
   # Download from IBKR website
   # https://www.interactivebrokers.com/en/trading/tws.php
   ```

2. **Enable API Access**
   - Open TWS/Gateway
   - Go to: **File → Global Configuration → API → Settings**
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Read-Only API (recommended for scanning)
   - Set Socket Port:
     - **7497** for TWS Paper Trading
     - **7496** for TWS Live Trading
     - **4002** for IB Gateway
   - Add **127.0.0.1** to Trusted IP addresses

3. **Market Data Permissions**
   - Ensure you have options market data subscriptions
   - Check: Account → Manage Account → Market Data Subscriptions

---

## 🚀 Installation

### 1. Clone Repository

```bash
cd /home/user/sec
# Files already in place
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: `ta-lib` requires system libraries:

```bash
# Ubuntu/Debian
sudo apt-get install libta-lib-dev

# macOS
brew install ta-lib

# Or install without ta-lib (optional dependency)
pip install -r requirements.txt --ignore-installed ta-lib
```

### 4. Configure Scanner

Edit `config.yaml` to customize:

```yaml
# IBKR connection settings
ibkr:
  tws:
    host: "127.0.0.1"
    port: 7497  # Change based on your setup

# Add your watchlist
watchlist:
  symbols:
    - "SPY"
    - "QQQ"
    - "NVDA"
    # Add more symbols...
```

### 5. Create Data Directory

```bash
mkdir -p data logs
```

---

## 💻 Usage

### Option 1: Web UI (Recommended)

```bash
# Start the web dashboard
./start_web.sh

# Open browser to http://localhost:5000
# Click "Start" button to begin scanning
```

**Features:**
- 📊 Real-time signal dashboard
- 📈 Interactive charts (P/C ratio, volume, distribution)
- 🎯 Watchlist management (add/remove symbols on the fly)
- ⚙️ Live configuration editor
- 📜 Scan history
- 🔔 Visual alerts and notifications
- 📱 Responsive design

See [WEB_UI_README.md](WEB_UI_README.md) for complete guide.

### Option 2: Command Line

```bash
# Activate virtual environment
source venv/bin/activate

# Start TWS or IB Gateway first!

# Run single scan
python scanner.py --mode once

# Run continuous scanning (every 60 seconds)
python scanner.py --mode continuous

# Scan specific symbols
python scanner.py --symbols SPY QQQ NVDA --mode once
```

### Command-Line Options

```bash
python scanner.py --help

Options:
  --mode {continuous,once}  Scan mode (default: once)
  --config CONFIG          Path to config file (default: config.yaml)
  --symbols [SYMBOLS ...]  Override watchlist with specific symbols
```

### Configuration

All scanner parameters are in `config.yaml`:

```yaml
# Whale Filters
whale_filters:
  liquidity_gate:
    min_volume: 500000
    min_oi: 100000

  anomaly_gate:
    pc_whale_threshold: 0.3
    pc_bullish_threshold: 0.7
    pc_bearish_threshold: 1.3

  conviction_gate:
    volume_vs_avg_multiplier: 2.0
    oi_delta_threshold: 25000

  volatility_gate:
    ivr_expensive: 80
    ivr_cheap: 20
```

---

## 📊 Understanding the Output

### Console Output

```
================================================================================
Scanning SPY...
================================================================================
SPY current price: $450.25
  P/C Ratio (Volume): 0.652
  P/C Ratio (OI): 0.891
  Total Volume: 2,450,000
  Total OI: 5,200,000

Liquidity Gate: 145 contracts passed
Anomaly Gate: 89 contracts passed
Conviction Gate: 23 contracts passed
Volatility Gate: 12 contracts passed

🐋 Whale activity detected for SPY!

🎯 HIGH CONVICTION COMBO SIGNALS:

  STRONG_BULL: Low P/C + High Call Volume + Rising Call OI
  P/C Ratio: 0.652
  Confidence: HIGH
```

### Signal Types

| Signal | Meaning | Action |
|--------|---------|--------|
| **EXTREME_BULLISH** | P/C < 0.5, massive call flow | BUY CALLS / SELL PUT SPREADS |
| **BULLISH** | P/C < 0.7, call accumulation | BUY CALLS |
| **EXTREME_BEARISH** | P/C > 1.5, massive put flow | BUY PUTS / SELL CALL SPREADS |
| **BEARISH** | P/C > 1.3, put accumulation | BUY PUTS |
| **CALL_HEDGE** | Call activity during bearish P/C | MONITOR - Likely hedge |
| **PUT_HEDGE** | Put activity during bullish P/C | MONITOR - Likely hedge |
| **RETAIL_FOMO** | Extreme P/C + no OI change | FADE (sell premium) |

---

## 🔍 Whale Detection Rules

### Volume vs Open Interest Patterns

| Pattern | Volume | OI | Interpretation | Action |
|---------|--------|----|--------------|----|
| **Conviction Trade** | High | High | Smart money building positions | FOLLOW |
| **Day Trading Noise** | High | Low | Retail day trading, no staying power | AVOID |
| **Breakout Setup** | Low | High | Trapped positions, coiled spring | WAIT for volume spike |
| **Normal Activity** | Normal | Normal | No anomaly | MONITOR |

### P/C Ratio Interpretation

- **< 0.3**: Extreme whale call buying
- **0.3 - 0.7**: Bullish (calls dominate)
- **0.7 - 1.3**: Neutral
- **1.3 - 1.5**: Bearish (puts dominate)
- **> 1.5**: Extreme whale put buying

### IV Rank Trading Rules

- **IVR > 90**: Sell premium (strangles, iron condors)
- **IVR 80-90**: Expensive volatility, consider selling
- **IVR 20-30**: Cheap volatility, consider buying
- **IVR < 10**: Buy options (calendars, diagonals)

---

## 📁 Project Structure

```
sec/
├── scanner.py              # Main CLI orchestrator
├── web_app.py              # Flask web application
├── ibkr_connection.py      # IBKR API connection handler
├── options_data.py         # Options data fetcher
├── whale_filters.py        # Whale detection filters
├── signal_detector.py      # Signal detection & alerts
├── data_storage.py         # Historical data storage
├── utils.py               # Helper functions
├── example_usage.py       # Usage examples
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── start_web.sh          # Web UI launcher
├── README.md             # Main documentation
├── WEB_UI_README.md      # Web UI guide
├── templates/            # HTML templates
│   └── dashboard.html
├── static/               # CSS, JS, assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── data/                 # SQLite database (auto-created)
│   └── whale_scanner.db
└── logs/                 # Log files (auto-created)
    └── whale_scanner.log
```

---

## 🛠️ Advanced Configuration

### Custom Watchlist

```yaml
watchlist:
  symbols:
    - "SPY"
    - "QQQ"
    - "IWM"

  # Scan all S&P 500 (requires implementation)
  scan_sp500: false
  scan_nasdaq100: false
```

### Scanning Parameters

```yaml
scanning:
  interval_seconds: 60  # Scan every 60 seconds

  expirations_to_scan:
    - 0   # 0 DTE
    - 1   # 1 DTE
    - 7   # 1 week
    - 30  # 1 month

  strikes_range: 20  # % above/below current price
```

### Alerts (Optional)

```yaml
alerts:
  # Telegram
  telegram:
    enabled: false
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"

  # Email
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your_email@gmail.com"
    password: "your_app_password"
```

---

## 🎓 Whale Trading Strategies

### 1. Following Smart Money (Conviction Trades)

**Conditions:**
- Volume > 2x average
- Rising OI in direction of flow
- P/C deviation > 1.5σ from average

**Action:** Trade in direction of whale flow

### 2. Fading Retail FOMO

**Conditions:**
- P/C < 0.3 (extreme bullish)
- Volume 5x+ average
- NO OI increase (retail day trading)

**Action:** Sell iron condors, fade the move

### 3. Institutional Hedging

**Conditions:**
- High P/C + Put volume spike
- IVR > 90 (panic hedging)
- Rising put OI

**Action:** Buy dips (institutions hedging, not selling)

### 4. Volatility Extremes

**High IVR (>90):**
- Sell strangles 1-2 DTE
- Sell premium pre-earnings

**Low IVR (<10):**
- Buy far-dated options
- Buy calendar spreads

---

## ⚠️ Risk Warnings

1. **This is a scanning tool, not trading advice**
2. **Always do your own analysis before trading**
3. **Options trading involves substantial risk**
4. **Past whale activity doesn't guarantee future performance**
5. **Use proper position sizing and risk management**
6. **Test with paper trading first**

---

## 🐛 Troubleshooting

### Connection Issues

**Error: Failed to connect to IBKR**

1. Ensure TWS/Gateway is running
2. Check API settings are enabled
3. Verify port number matches config (7497/7496/4002)
4. Confirm 127.0.0.1 is in trusted IPs

### Data Issues

**Error: No option data found**

1. Check you have options market data subscriptions
2. Verify symbol is correct and has liquid options
3. Try increasing `strikes_range` in config
4. Check market hours (scanner works during market hours)

### Performance Issues

**Scanner is slow**

1. Reduce number of symbols in watchlist
2. Reduce `strikes_range` (scan fewer strikes)
3. Reduce `expirations_to_scan` list
4. Increase `interval_seconds` for continuous mode

---

## 📈 Roadmap

- [ ] Real-time streaming data (vs snapshot)
- [ ] Web dashboard for visualization
- [ ] Backtesting framework
- [ ] Machine learning signal enhancement
- [ ] Multi-leg options scanner (spreads, iron condors)
- [ ] Integration with other brokers (TD Ameritrade, Schwab)
- [ ] Discord/Slack notifications
- [ ] Mobile app

---

## 📝 License

This project is for educational purposes. Use at your own risk.

---

## 🙏 Credits

**Created for Evermont Trading**

Built with:
- [ib_insync](https://github.com/erdewit/ib_insync) - IBKR API wrapper
- [IBKR API](https://www.interactivebrokers.com/en/trading/ib-api.php)

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review IBKR API documentation
3. Verify TWS/Gateway configuration

---

## ⚡ Quick Reference

### Start Scanner
```bash
source venv/bin/activate
python scanner.py --mode once
```

### Check if TWS is Ready
- TWS/Gateway is running
- API settings enabled
- Paper/Live mode selected
- Market data active

### Key Whale Signals
- P/C < 0.3 + Volume 5x = 🔥 Extreme activity
- High Vol + Rising OI = Follow smart money
- High Vol + Low OI = Day trading noise (avoid)
- IVR > 90 = Sell premium opportunity
- IVR < 20 = Buy options opportunity

Happy whale hunting! 🐋📈
