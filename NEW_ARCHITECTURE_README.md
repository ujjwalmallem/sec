# Whale Scanner - New Architecture

## Complete Rebuild from Scratch

This is a **complete rewrite** of the IBKR Whale Options Scanner with a clean, modern architecture focused on:
- **Tradier API** as the primary data source
- **PostgreSQL** for storing tickers, whale rules, signals, and metrics
- **Configurable whale rules** stored in database (no code changes needed)
- **Clean separation** of concerns
- **RESTful API** for all operations
- **Modern web dashboard** for monitoring

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Web Dashboard                         │
│              (React-style vanilla JS)                   │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP/REST
┌───────────────────▼─────────────────────────────────────┐
│                   REST API Server                        │
│                  (api_server.py)                        │
│  - Ticker management                                    │
│  - Rule management                                      │
│  - Signal viewing                                       │
│  - Scanner control                                      │
└───────────┬───────────────────┬─────────────────────────┘
            │                   │
┌───────────▼────────┐ ┌───────▼──────────────────────────┐
│  Whale Scanner     │ │   Database Storage              │
│  (whale_scanner.py)│ │   (database_storage.py)         │
└───────────┬────────┘ └───────┬──────────────────────────┘
            │                   │
┌───────────▼────────┐ ┌───────▼──────────────────────────┐
│   Rule Engine      │ │   PostgreSQL Database           │
│  (rule_engine.py)  │ │   - tickers                     │
│  - Evaluates rules │ │   - whale_rules                  │
│  - Detects signals │ │   - whale_signals                │
└───────────┬────────┘ │   - historical_metrics           │
            │           │   - option_contracts             │
┌───────────▼────────┐ │   - scan_runs                    │
│  Tradier Client    │ └──────────────────────────────────┘
│ (tradier_client.py)│
│  - Options chains  │
│  - Greeks          │
│  - Real-time data  │
└────────────────────┘
```

---

## 📁 New Files

### Core Modules

1. **`tradier_client.py`** (350 lines)
   - Clean Tradier API client
   - Rate limiting
   - Automatic metrics calculation
   - Sandbox/production support

2. **`database_storage.py`** (800 lines)
   - PostgreSQL data access layer
   - Connection pooling
   - CRUD operations for all entities
   - Clean API

3. **`rule_engine.py`** (600 lines)
   - Evaluates whale detection rules
   - Four-gate filtering system
   - Signal detection (10+ signal types)
   - Combo signals
   - All rules configurable via database

4. **`whale_scanner.py`** (400 lines)
   - Live scanner orchestration
   - Fetches data from Tradier
   - Evaluates rules
   - Stores signals
   - One-time or continuous modes

5. **`api_server.py`** (300 lines)
   - Flask REST API
   - Ticker management
   - Rule management
   - Signal viewing
   - Scanner control (start/stop/run-once)
   - Serves web dashboard

### Database

6. **`database/whale_scanner_schema.sql`** (350 lines)
   - Complete PostgreSQL schema
   - 6 tables with proper indexes
   - 4 views for common queries
   - **All whale rules pre-loaded**
   - Default watchlist included

### Web UI

7. **`templates/whale_dashboard.html`**
   - Modern, dark-themed dashboard
   - Real-time signal monitoring
   - Ticker management
   - Rule viewing
   - Scanner control

8. **`static/css/dashboard.css`**
   - Professional styling
   - Responsive design

9. **`static/js/dashboard.js`**
   - Dashboard interactivity
   - REST API integration
   - Auto-refresh

---

## 🎯 Key Features

### 1. Database-Driven Rules

**All whale trading rules are stored in PostgreSQL!**

No more hardcoded logic. Rules are configured in the `whale_rules` table:

```sql
SELECT * FROM whale_rules WHERE rule_type = 'FILTER';
```

**Pre-loaded rules:**
- Liquidity Gate (volume/OI thresholds)
- Anomaly Gate (P/C ratio deviation)
- Conviction Gate (volume vs avg + OI growth)
- Volatility Gate (IV rank extremes)
- Strong Bull Signal
- Institutional Hedge
- Retail FOMO
- Smart Money Long
- Short Squeeze Fuel
- IV Crush Opportunity
- Whale Conviction (combo)
- Custom Scanner (combo)

### 2. Configurable Parameters

Each rule has a `rule_config` JSONB field:

```json
{
  "min_volume": 500000,
  "min_oi": 100000,
  "pc_deviation_threshold": 1.5,
  "ivr_expensive": 80
}
```

**Update via API:**
```bash
PUT /api/rules/liquidity_gate
{
  "config": {
    "min_volume": 1000000,
    "min_oi": 200000
  }
}
```

### 3. Clean Architecture

- **Single Responsibility**: Each module has one job
- **Dependency Injection**: Components can be easily tested
- **Type Hints**: Better IDE support and documentation
- **Logging**: Comprehensive logging at all levels
- **Error Handling**: Graceful degradation

### 4. RESTful API

All operations via clean REST endpoints:

```
GET  /api/tickers                 # List tickers
POST /api/tickers                 # Add ticker
DELETE /api/tickers/{symbol}      # Remove ticker

GET  /api/rules                   # List rules
GET  /api/rules?type=FILTER       # Filter by type
PUT  /api/rules/{name}            # Update rule config
POST /api/rules/{name}/toggle     # Enable/disable rule

GET  /api/signals                 # Get active signals
GET  /api/signals?symbol=SPY      # Filter by symbol

POST /api/scanner/run-once        # Run scan once
POST /api/scanner/start           # Start continuous
POST /api/scanner/stop            # Stop scanner

GET  /api/dashboard               # Watchlist with metrics
GET  /api/scans/recent            # Recent scan history
```

### 5. Web Dashboard

Modern, single-page dashboard with:
- Real-time signal display
- Ticker management (add/remove)
- Rule browsing
- Scanner control (start/stop/run-once)
- Recent scan history
- Auto-refresh every 30 seconds

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

**Required settings in `.env`:**
```env
# Database (auto-created by Docker)
POSTGRES_PASSWORD=your_secure_password

# Tradier API
TRADIER_API_KEY=YapJSqXqDZ5ui8HtoP7QEyIX7CIk
TRADIER_ACCOUNT_ID=VA31706838
TRADIER_SANDBOX=true
```

### 2. Start with Docker

```bash
# Start PostgreSQL + API server
docker-compose up -d

# View logs
docker-compose logs -f api

# Check status
docker-compose ps
```

### 3. Access Dashboard

Open browser: **http://localhost:8000**

---

## 📊 Using the Scanner

### Via Web Dashboard (Recommended)

1. Open http://localhost:8000
2. Click "Run Scan Once" to test
3. View detected signals in real-time
4. Click "Start Continuous" for live monitoring

### Via CLI

```bash
# One-time scan
docker-compose exec api python whale_scanner.py --mode once

# Continuous (60s interval)
docker-compose exec api python whale_scanner.py --mode continuous --interval 60
```

### Via API

```bash
# Run once
curl -X POST http://localhost:8000/api/scanner/run-once

# Start continuous
curl -X POST http://localhost:8000/api/scanner/start \
  -H "Content-Type: application/json" \
  -d '{"interval": 60}'

# Stop
curl -X POST http://localhost:8000/api/scanner/stop
```

---

## 🗄️ Database Schema

### Tables

1. **`tickers`** - Watchlist symbols
2. **`whale_rules`** - Configurable detection rules (FILTER, SIGNAL, COMBO)
3. **`scan_runs`** - Tracks each scanner execution
4. **`historical_metrics`** - Time-series aggregated metrics per symbol
5. **`option_contracts`** - Individual option contract snapshots
6. **`whale_signals`** - Detected whale signals

### Views

1. **`latest_metrics`** - Most recent metrics for each symbol
2. **`active_signals`** - Active whale signals with context
3. **`top_volume_today`** - Top 100 volume options today
4. **`watchlist_dashboard`** - Watchlist with latest metrics

---

## 🎨 Whale Rules Explained

### Four-Gate Filtering System

Scanner applies **4 sequential gates**. All must pass:

**Gate 1: Liquidity**
- Total volume > 500K contracts
- Total OI > 100K contracts
- Ensures we're looking at liquid options

**Gate 2: Anomaly**
- P/C ratio deviates >1.5σ from 20-day average
- Detects unusual call/put activity

**Gate 3: Conviction**
- Volume > 2x average
- OI delta > 25K (new positions being opened)
- Separates real conviction from noise

**Gate 4: Volatility**
- IV Rank in top 10% (expensive) or bottom 10% (cheap)
- Identifies extremes for signal context

### Signal Detection Rules

After passing gates, signal rules are evaluated:

**Strong Bull Signal**
- P/C ratio ≤ 0.7
- Call volume > 2x avg
- Call OI increasing
- IV Rank < 30
- **Action: FOLLOW**

**Institutional Hedge**
- P/C ratio ≥ 1.3
- Put volume spike (3x avg)
- Put OI increasing
- IV Rank > 90
- **Action: BUY_DIPS**

**Retail FOMO**
- P/C ratio < 0.3
- Volume 5x avg
- OI change < 1000 (no new positions)
- **Action: FADE**

**Smart Money Long**
- Call OI ↑ + Price ↑
- **Action: FOLLOW**

**Short Squeeze Fuel**
- Put OI ↓ + Price ↓
- **Action: BUY_CALLS**

**And more...**

### Combo Signals (High Conviction)

**Whale Conviction**
- Volume > 2x avg
- P/C deviation > 1.5σ
- OI delta > 10K
- IV extreme (rank >80 or <20)
- **Action: STRONG_FOLLOW**

**Custom Scanner**
- Volume spike + P/C anomaly + OI change + IV extremes
- **Action: ALERT**

---

## 🛠️ Customizing Rules

### Update Rule Configuration

```python
# Via Python
from database_storage import DatabaseStorage

db = DatabaseStorage()

# Update liquidity thresholds
db.update_rule_config('liquidity_gate', {
    'min_volume': 1000000,  # Raise to 1M
    'min_oi': 200000        # Raise to 200K
})

# Update P/C thresholds
db.update_rule_config('anomaly_gate', {
    'pc_deviation_threshold': 2.0,  # More stringent
    'pc_lookback_days': 30          # Longer history
})
```

### Via API

```bash
curl -X PUT http://localhost:8000/api/rules/liquidity_gate \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "min_volume": 1000000,
      "min_oi": 200000
    }
  }'
```

### Enable/Disable Rules

```bash
# Disable retail FOMO detection
curl -X POST http://localhost:8000/api/rules/retail_fomo/toggle \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## 📈 Example Workflow

1. **Scanner runs** (manual or continuous)
2. **Fetches options data** from Tradier for all watchlist tickers
3. **Calculates metrics** (volume, OI, P/C ratios, IV)
4. **Saves to `historical_metrics`** table
5. **Evaluates filter rules** (4 gates) via `rule_engine`
6. If passed, **evaluates signal rules**
7. **Saves detected signals** to `whale_signals` table
8. **Dashboard auto-refreshes** and displays new signals
9. **Repeat** after interval

---

## 🔧 Development

### Run Components Separately

```bash
# Database only
docker-compose up postgres

# API server (after DB is up)
python api_server.py

# Scanner CLI
python whale_scanner.py --mode once

# Interactive Python
python
>>> from tradier_client import TradierClient
>>> client = TradierClient()
>>> client.get_quote(['SPY'])
```

### Testing

```bash
# Test Tradier connection
python tradier_client.py

# Test database
python database_storage.py

# Test rule engine
python rule_engine.py

# Test scanner
python whale_scanner.py --mode once
```

---

## 🚢 Docker Deployment

### Simple (2 containers)

- **postgres** - PostgreSQL database
- **api** - API server + dashboard

```bash
docker-compose up -d
```

**Ports:**
- **8000** - Web dashboard + API
- **5432** - PostgreSQL (internal)

**Volumes:**
- `postgres_data` - Database persistence
- `./data` - Local data files
- `./logs` - Application logs

---

## 🆚 Old vs New Architecture

| Feature | Old | New |
|---------|-----|-----|
| **Rules** | Hardcoded in Python | Database-driven JSONB |
| **Data Source** | IBKR + Tradier | Tradier only (cleaner) |
| **Configuration** | YAML files | Database + REST API |
| **UI** | Multiple Flask apps | Single unified dashboard |
| **Scanner Control** | Separate scripts | API-driven (start/stop/run-once) |
| **Docker Services** | 4 containers | 2 containers |
| **Code Complexity** | ~3000 lines | ~2500 lines (cleaner) |
| **Modularity** | Mixed concerns | Clean separation |
| **Testing** | Difficult | Each module testable |

---

## 📝 Summary

This is a **production-ready, from-scratch rebuild** with:

✅ Clean, modular architecture
✅ Database-driven whale rules
✅ RESTful API for all operations
✅ Modern web dashboard
✅ Tradier API integration
✅ PostgreSQL for data persistence
✅ Docker deployment
✅ Configurable everything
✅ Comprehensive logging
✅ Easy to extend

**No more editing code to change rules. Everything is configurable via database or API.**

---

## 🎓 Next Steps

1. **Customize watchlist**: Add your favorite tickers via dashboard
2. **Adjust rules**: Tune thresholds via API to match your strategy
3. **Run scans**: Start with "Run Once" to test, then enable continuous
4. **Monitor signals**: Watch for whale activity in real-time
5. **Extend**: Add custom rules, new signal types, or integrations

---

Built from scratch for maximum clarity, maintainability, and performance. 🐋
