# Tradier API Integration Guide

## Overview

The whale scanner now supports **Tradier API** as an alternative to IBKR TWS! This means:

✅ **No TWS installation required** - Works with just API token
✅ **No ARCA subscription errors** - Tradier provides clean market data
✅ **Simpler setup** - Just add your API token to config
✅ **Same whale detection** - All filters and signals work identically

## Important: IP Whitelisting

⚠️ **Tradier API is IP-restricted** by default. You must whitelist the IP address you'll be running the scanner from:

1. **For local development** (Your MacBook): Already works! Your curl test succeeded.
2. **For deployment servers**: You need to whitelist the server's public IP address in your Tradier account settings.

### How to Whitelist IPs in Tradier

1. Log in to your Tradier account at https://dash.tradier.com
2. Go to **API Settings** or **Security Settings**
3. Add your server's public IP address to the whitelist
4. Save changes and wait a few minutes for changes to propagate

### Finding Your Server's IP

```bash
curl ifconfig.me
```

## Setup Instructions

### 1. Get Your Tradier Credentials

You already have these:
- **API Token**: `YapJSqXqDZ5ui8HtoP7QEyIX7CIk`
- **Account ID**: `VA31706838`
- **Environment**: Sandbox (for testing)

### 2. Update config.yaml

The config has already been updated with your credentials:

```yaml
# Data Source Selection
data_source:
  provider: "tradier"         # Set to "tradier" or "ibkr"

# Tradier Connection Settings
tradier:
  api_token: "YapJSqXqDZ5ui8HtoP7QEyIX7CIk"
  sandbox: true               # true = sandbox, false = production
  account_id: "VA31706838"
```

**To switch between Tradier and IBKR**, just change the `provider` value:
- `provider: "tradier"` - Use Tradier API (recommended)
- `provider: "ibkr"` - Use IBKR TWS API

### 3. Install Dependencies

```bash
# All dependencies are already included in requirements.txt
pip install -r requirements.txt
```

### 4. Run the Scanner

#### CLI Scanner
```bash
python scanner.py
```

#### Web UI
```bash
python web_app.py
# Then open http://localhost:8080 in your browser
```

## Key Differences from IBKR

### What's the Same
- All whale detection filters (Liquidity, Anomaly, Conviction, Volatility Gates)
- P/C ratio calculations
- Signal detection (Strong Bull, Institutional Hedge, Retail FOMO)
- Web UI and dashboard
- Data storage and historical tracking

### What's Different
- **No TWS required** - Direct REST API calls
- **Simpler authentication** - Just an API token
- **No Greek data** - Tradier doesn't provide Delta, Gamma, etc. (can calculate if needed)
- **No historical options volume** - Tradier only provides current snapshot
- **15-minute delayed data** - Free tier has slight delay (fine for whale detection)

### Limitations
- **Historical OI deltas** are not available (we track current OI only)
- **Greeks (Delta, Gamma, etc.)** are not provided by Tradier
  - Can be calculated using Black-Scholes if needed
- **Options historical data** is limited compared to IBKR
- **IP whitelist required** for API access

## Troubleshooting

### Error: "Access denied" (403)

**Cause**: Your IP address is not whitelisted in Tradier account

**Solution**:
1. Get your public IP: `curl ifconfig.me`
2. Log in to Tradier dashboard
3. Add your IP to the API whitelist
4. Wait 5-10 minutes for changes to propagate
5. Test again: `python tradier_connection.py`

### Error: "Tradier modules not available"

**Cause**: Missing tradier integration files

**Solution**:
```bash
# Verify these files exist:
ls -l tradier_connection.py
ls -l tradier_options_data.py

# If missing, they should be in your repo
```

### No Options Data Returned

**Cause**: Symbol doesn't have active options, or market is closed

**Solution**:
- Verify market is open during trading hours
- Try a highly liquid symbol like SPY
- Check expirations are available: `python tradier_connection.py`

### Scanner Showing No Signals

**Cause**: Sandbox data might not have realistic volume/OI

**Solution**:
- Sandbox data is simulated and may not trigger whale filters
- For production use, switch to production Tradier API:
  ```yaml
  tradier:
    sandbox: false  # Use live market data
    api_token: "YOUR_PRODUCTION_TOKEN"
  ```

## Testing the Integration

### Test Basic Connection
```bash
python tradier_connection.py
```

Expected output:
```
✓ Authenticated! Account: VA31706838
✓ Connected to Tradier API
```

### Test Data Fetching
```bash
python tradier_options_data.py
```

Expected output:
```
✓ Successfully fetched X contracts
P/C Ratio (volume): X.XXX
```

### Test Full Scanner
```bash
python scanner.py
```

Expected output:
```
Data provider: TRADIER
✓ Using Tradier API (no TWS required!)
Scanning SPY...
```

## Production Deployment

### 1. Switch to Production API

Update `config.yaml`:
```yaml
tradier:
  sandbox: false
  api_token: "YOUR_PRODUCTION_API_TOKEN"  # Get from Tradier dashboard
```

### 2. Whitelist Production Server IP

```bash
# On your production server, get the IP
curl ifconfig.me

# Add this IP to Tradier API whitelist
```

### 3. Test Connection

```bash
python tradier_connection.py
```

### 4. Deploy

```bash
# Start web app with production config
python web_app.py

# Or use systemd service (see WEB_UI_README.md)
```

## Comparison: Tradier vs IBKR

| Feature | Tradier | IBKR |
|---------|---------|------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐⭐ Complex |
| **Authentication** | API Token | TWS/Gateway + Port |
| **Options Data** | ✅ Yes | ✅ Yes |
| **Volume & OI** | ✅ Yes | ✅ Yes |
| **Implied Volatility** | ✅ Yes | ✅ Yes |
| **Greeks** | ❌ No | ✅ Yes |
| **Historical Data** | ⚠️ Limited | ✅ Full |
| **Real-time Data** | ⚠️ Delayed 15min | ✅ Real-time |
| **Whale Detection** | ✅ Full Support | ✅ Full Support |
| **Cost** | 💰 Free Sandbox | 💰 Free w/ Account |
| **IP Restrictions** | ⚠️ Must Whitelist | ✅ No Restrictions |

## Recommendation

- **Development & Testing**: Use Tradier Sandbox (simpler, no TWS needed)
- **Production (Casual)**: Use Tradier Production (15-min delay is fine for whale detection)
- **Production (Professional)**: Use IBKR (real-time data, full Greeks)

## Support

For Tradier API issues:
- Documentation: https://documentation.tradier.com/brokerage-api
- Support: support@tradier.com

For Scanner Issues:
- Check logs in `logs/whale_scanner.log`
- Run with debug mode: Set `logging: level: DEBUG` in config.yaml
- Open GitHub issue with error details

## Next Steps

1. **✅ Whitelist your IP** in Tradier dashboard
2. **Test connection**: `python tradier_connection.py`
3. **Run scanner**: `python scanner.py`
4. **Start web UI**: `python web_app.py`
5. **Monitor signals**: Open http://localhost:8080

Enjoy whale hunting! 🐋
