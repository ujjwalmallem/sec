# 🌐 Whale Scanner Web UI - User Guide

![Whale Scanner](https://img.shields.io/badge/Status-Active-success)
![Version](https://img.shields.io/badge/Version-1.0-blue)

## 🚀 Quick Start

### 1. Start the Web UI

```bash
# Make sure you've run setup first
./setup.sh

# Start the web application
./start_web.sh
```

The dashboard will be available at: **http://localhost:5000**

### 2. Before Scanning

✅ **Start IBKR TWS or Gateway**
- Open TWS or IB Gateway
- Enable API connections (File → Global Config → API → Settings)
- Port 7497 (paper) or 7496 (live)

### 3. Use the Dashboard

1. Open http://localhost:5000 in your browser
2. Add symbols to your watchlist
3. Click **"Start"** button to begin scanning
4. Monitor real-time signals as they appear
5. Click **"Stop"** when done

---

## 📊 Dashboard Overview

### Main Interface

```
┌─────────────────────────────────────────────────────────────┐
│  🐋 Whale Options Scanner                    🟢 Connected   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐  ┌──────────────────────────────────────┐│
│  │  CONTROLS     │  │  LIVE SIGNALS                        ││
│  │               │  │  ╔══════════════════════════════════╗││
│  │  📊 Status    │  │  ║ Time | Symbol | Type | Volume  ║││
│  │  📝 Watchlist │  │  ║ 14:23│  SPY   │ BULL │ 125K    ║││
│  │  📈 Stats     │  │  ║ 14:21│  QQQ   │ BEAR │  98K    ║││
│  │               │  │  ╚══════════════════════════════════╝││
│  └───────────────┘  └──────────────────────────────────────┘│
│                                                               │
│  [Charts] [History] [Configuration]                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Features

### 1. Real-Time Signal Display

**Live Signals Tab** shows:
- ⏰ **Time** - When signal was detected
- 📊 **Symbol** - Underlying stock ticker
- 🎯 **Type** - Signal classification (BULLISH, BEARISH, etc.)
- 📝 **Contract** - Strike, right (C/P), and DTE
- 📈 **Volume** - Options volume
- 🏦 **Open Interest** - OI
- 📊 **P/C Ratio** - Put/Call ratio with indicator
- 💡 **Signal Type** - Action recommendation
- ⚡ **Strength** - Signal strength (0-100) with visual bar

**Signal Types:**
- 🔵 **EXTREME BULLISH** - P/C < 0.5, massive call flow
- 🟢 **BULLISH** - Strong call activity
- 🔴 **BEARISH** - Strong put activity
- 🟣 **EXTREME BEARISH** - P/C > 1.5, massive put flow
- ⚠️ **RETAIL FOMO** - Fade signal (high vol, no OI)
- 🛡️ **HEDGE** - Institutional hedging activity

### 2. Interactive Charts

**Charts Tab** includes:

#### P/C Ratio Trends
- Real-time put/call ratio over time
- Helps identify shifts in market sentiment

#### Volume Analysis
- Call vs Put volume by symbol
- Bar chart showing relative activity

#### Signal Distribution
- Pie chart: Bullish vs Bearish vs Neutral
- Quick visual of market bias

#### Whale Activity Heatmap
- Horizontal bar chart
- Shows which symbols have most whale activity

### 3. Watchlist Management

**Add Symbols:**
1. Type symbol in input box (e.g., "SPY")
2. Click "Add Symbol" or press Enter
3. Symbol appears in watchlist

**Remove Symbols:**
- Click ❌ button next to symbol
- Symbol removed from scanning

**Active Scanning Indicator:**
- Symbols being scanned turn **green** during scan
- Easy visual feedback of scanner progress

### 4. Scanner Controls

#### Status Panel
- **Scanner Status** - Running/Stopped with pulse animation
- **IBKR Status** - Connected/Disconnected
- **Last Scan** - Timestamp of most recent scan
- **Total Scans** - Counter of completed scans

#### Control Buttons
- **🟢 Start** - Begin continuous scanning
- **🔴 Stop** - Halt scanner
- Connection status badge shows real-time status

#### Quick Stats
- **Total Signals** - All signals detected
- **Whale Signals** - High-strength signals (>75)
- **Symbols Scanned** - Unique symbols with signals

### 5. Scan History

**History Tab** shows:
- Scan number
- Timestamp
- Symbols scanned
- Signals found
- Duration

**Use Cases:**
- Track scanner performance
- Review past scans
- Identify high-activity periods

### 6. Configuration Editor

**Configuration Tab** allows real-time adjustment of:

**Liquidity Gate:**
- Min Volume (default: 500,000)
- Min Open Interest (default: 100,000)

**Anomaly Gate:**
- P/C Whale Threshold (default: 0.3)
- P/C Deviation σ (default: 1.5)

**Conviction Gate:**
- Volume Multiplier (default: 2.0x)
- OI Delta Threshold (default: 25,000)

**Volatility Gate:**
- IVR Expensive threshold (default: 80)
- IVR Cheap threshold (default: 20)

**Scanning:**
- Scan Interval in seconds (default: 60)

**Save Changes:**
- Click "Save Configuration" to apply
- Restart scanner for changes to take effect

---

## 🎨 Visual Indicators

### Connection Status
- 🟢 **Green dot (pulsing)** - Connected and healthy
- 🔴 **Red dot** - Disconnected

### Scanner Status
- 🟢 **Running** - Pulsing green badge
- ⚪ **Stopped** - Gray badge

### P/C Ratio Colors
- 🔵 **Dark Blue** - P/C < 0.5 (EXTREME BULLISH)
- 🟢 **Green** - P/C 0.5-0.7 (BULLISH)
- ⚪ **Gray** - P/C 0.7-1.3 (NEUTRAL)
- 🟠 **Orange** - P/C 1.3-1.5 (BEARISH)
- 🔴 **Red** - P/C > 1.5 (EXTREME BEARISH)

### Signal Strength Bar
- 🟡 **Yellow** - 0-49 (Low)
- 🟠 **Orange** - 50-74 (Medium)
- 🟢 **Green** - 75-89 (High)
- 🔵 **Blue (glowing)** - 90-100 (Extreme)

---

## 🔔 Real-Time Updates

### Socket.IO Connection
The UI uses **WebSockets** for real-time updates:

- ✅ Instant signal notifications
- ✅ Live scan progress
- ✅ Connection status changes
- ✅ Error alerts

**Toast Notifications** appear for:
- Connection status changes
- Scanner start/stop
- Errors and warnings
- Watchlist updates

---

## 💡 Usage Tips

### Best Practices

1. **Start Small**
   - Begin with 3-5 symbols
   - Monitor performance
   - Add more as needed

2. **Adjust Scan Interval**
   - 60 seconds for most use cases
   - 30 seconds for high-frequency
   - 120+ seconds for low bandwidth

3. **Watch Signal Strength**
   - Focus on signals with strength > 75
   - These are high-conviction whale moves

4. **Monitor P/C Ratio**
   - P/C < 0.3 = Major whale activity
   - P/C < 0.5 or > 1.5 = Extreme moves
   - Look for rapid P/C changes

5. **Volume/OI Divergence**
   - High volume + low OI = Day trading noise
   - High volume + high OI = Conviction trade
   - Low volume + high OI = Breakout setup

### Keyboard Shortcuts

- **Enter** in symbol input - Add symbol
- **Ctrl+R** - Refresh page (doesn't stop scanner)
- **F5** - Hard refresh

---

## 🐛 Troubleshooting

### Issue: "Disconnected" Badge

**Solution:**
1. Check IBKR TWS/Gateway is running
2. Verify API settings are enabled
3. Confirm port number (7497/7496)
4. Restart web server: `./start_web.sh`

### Issue: No Signals Appearing

**Possible Causes:**
1. **Market is closed** - Scanner works best during market hours
2. **No whale activity** - Not every scan finds signals
3. **Filters too strict** - Adjust configuration
4. **No market data** - Check IBKR subscriptions

### Issue: Scanner Won't Start

**Solutions:**
1. Check IBKR connection status
2. Verify TWS/Gateway is running
3. Ensure API is enabled
4. Check console for errors (F12 in browser)

### Issue: Slow Performance

**Solutions:**
1. Reduce number of symbols in watchlist
2. Increase scan interval
3. Close other tabs/programs
4. Check network connection

### Issue: Configuration Won't Save

**Solution:**
1. Check file permissions on config.yaml
2. Ensure write access to directory
3. Check console for errors
4. Restart web server

---

## 🔧 Advanced Usage

### Running on Different Port

Edit `web_app.py`:
```python
socketio.run(app, host='0.0.0.0', port=8080, debug=False)
```

### Remote Access

To access from another device on network:

1. Find your local IP: `ifconfig` or `ipconfig`
2. Edit `web_app.py`:
   ```python
   socketio.run(app, host='0.0.0.0', port=5000)
   ```
3. Access from other device: `http://YOUR_IP:5000`

⚠️ **Security Warning:** Only use on trusted networks!

### Multiple Instances

To run multiple scanners:

1. Copy scanner directory
2. Change port in each instance
3. Use different IBKR client IDs in config.yaml

### API Endpoints

For custom integrations:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Scanner status |
| `/api/signals` | GET | Current signals |
| `/api/watchlist` | GET/POST | Manage watchlist |
| `/api/config` | GET/POST | Configuration |
| `/api/history/<symbol>` | GET | Historical data |
| `/api/recent_scans` | GET | Scan history |

**Example API Call:**
```bash
curl http://localhost:5000/api/status
```

---

## 📱 Browser Compatibility

**Recommended Browsers:**
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

**Mobile Browsers:**
- ✅ Chrome Mobile
- ✅ Safari iOS
- ⚠️ Layout optimized for desktop

---

## 🚨 Important Notes

### Market Data Requirements
- Options market data subscriptions required
- Check IBKR account for available data
- Some symbols may not have options data

### Rate Limiting
- IBKR API has rate limits
- Scanner automatically paces requests
- Don't scan too many symbols simultaneously

### Paper vs Live Trading
- **Paper Trading** (port 7497) - Safe for testing
- **Live Trading** (port 7496) - Real money at risk
- Always test with paper account first!

### Data Storage
- Signals stored in SQLite database
- Historical data in `data/whale_scanner.db`
- Logs in `logs/` directory

---

## 🆘 Getting Help

**Check These First:**
1. Browser console (F12) for JavaScript errors
2. Terminal output where web server is running
3. `logs/whale_scanner.log` for detailed logs

**Common Solutions:**
- Refresh browser page
- Restart web server
- Restart IBKR TWS/Gateway
- Check network connection

---

## 🎯 Feature Roadmap

**Coming Soon:**
- [ ] Email/SMS alerts from web UI
- [ ] Export signals to CSV
- [ ] Historical signal replay
- [ ] Custom alert rules
- [ ] Mobile app
- [ ] Dark mode theme
- [ ] Multi-timeframe analysis

---

## 📞 Support

For issues or questions:
1. Review this documentation
2. Check troubleshooting section
3. Verify IBKR configuration
4. Review scanner logs

---

**Built for Evermont Trading** - Happy Whale Hunting! 🐋📈

---

## 🔥 Quick Reference

### Starting the UI
```bash
./start_web.sh
```

### Default URL
```
http://localhost:5000
```

### Key Features
- ✅ Real-time whale signal detection
- ✅ Interactive charts
- ✅ Watchlist management
- ✅ Configuration editor
- ✅ Scan history

### Must-Have Setup
1. ✅ IBKR TWS/Gateway running
2. ✅ API enabled in IBKR
3. ✅ Virtual environment activated
4. ✅ Dependencies installed
5. ✅ config.yaml configured

### Signal Interpretation
- **Strength > 90** = Extreme whale activity
- **Strength 75-89** = High confidence
- **Strength 50-74** = Medium confidence
- **Strength < 50** = Low confidence

### P/C Ratio Guide
- **< 0.3** = 🐋 Whale calls
- **0.3-0.7** = Bullish
- **0.7-1.3** = Neutral
- **1.3-1.5** = Bearish
- **> 1.5** = 🐋 Whale puts

---

**End of Web UI Guide**
