# PostgreSQL Integration Guide

## Overview

The whale scanner now supports **PostgreSQL** for storing:
- ✅ Watchlist symbols (manage via database instead of config file)
- ✅ Historical metrics (P/C ratios, volume, OI over time)
- ✅ Option contract snapshots (every scan)
- ✅ Whale signals (detected signals with metadata)
- ✅ Scan run history (track scanner performance)

## Benefits

### Why PostgreSQL?

**vs SQLite (default):**
- 📊 **Better Analytics** - Complex queries, joins, aggregations
- 🔄 **Concurrent Access** - Multiple users/processes can access simultaneously
- 📈 **Scale** - Handles millions of option contracts efficiently
- 🔍 **Advanced Queries** - Window functions, CTEs, full-text search
- 🛡️ **Data Integrity** - Better constraint enforcement and transactions
- 📱 **Remote Access** - Can connect from visualization tools (Grafana, Tableau)

**Use Cases:**
- Track options volume/OI changes over days/weeks/months
- Build custom dashboards with historical data
- Analyze whale pattern effectiveness
- Share data across multiple scanner instances
- Export data for backtesting strategies

## Prerequisites

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**macOS (Postgres.app):**
1. Download from https://postgresapp.com
2. Open Postgres.app
3. Click "Initialize" to create default server

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
1. Download from https://www.postgresql.org/download/windows/
2. Run installer
3. Remember the password you set for `postgres` user

### 2. Verify Installation

```bash
# Check PostgreSQL is running
psql --version

# Connect to PostgreSQL (macOS/Linux)
psql postgres

# Windows (from SQL Shell)
psql -U postgres
```

## Quick Setup

### Step 1: Update Configuration

Edit `config.yaml`:

```yaml
# PostgreSQL Database Settings
postgres:
  enabled: true                    # Enable PostgreSQL storage
  host: "localhost"
  port: 5432
  database: "whale_scanner"
  user: "postgres"
  password: "your_password_here"   # Set your PostgreSQL password
```

**For macOS with Postgres.app** (no password by default):
```yaml
postgres:
  enabled: true
  host: "localhost"
  port: 5432
  database: "whale_scanner"
  user: "postgres"
  password: ""   # Leave empty for local development
```

### Step 2: Install Python Dependencies

```bash
pip install psycopg2-binary
# or
pip install -r requirements.txt
```

### Step 3: Create Database

Run the setup script:

```bash
python database/setup_postgres.py
```

This will:
- Create `whale_scanner` database
- Create all tables (watchlist_symbols, option_contracts, historical_metrics, etc.)
- Insert default watchlist (SPY, QQQ, AAPL, etc.)
- Create views for common queries

**Expected Output:**
```
🐋 Whale Scanner - PostgreSQL Setup
============================================================

1. Connecting to PostgreSQL server...
   ✓ Connected to PostgreSQL at localhost:5432

2. Checking if database 'whale_scanner' exists...
   → Creating database 'whale_scanner'...
   ✓ Created database 'whale_scanner'

3. Running schema script...
   ✓ Schema created successfully

4. Created 5 tables:
     - historical_metrics
     - option_contracts
     - scan_runs
     - watchlist_symbols
     - whale_signals

5. Watchlist initialized with 10 symbols

6. Testing connection...
   ✓ Connection successful!

   Database Statistics:
   - Active Symbols: 10
   - Historical Metrics: 0
   - Option Contracts: 0
   - Whale Signals: 0

============================================================
✅ PostgreSQL Setup Complete!
============================================================
```

### Step 4: Run the Scanner

```bash
# CLI scanner
python scanner.py

# Web UI
python web_app.py
```

The scanner will now:
- Load watchlist from PostgreSQL
- Store all option contract snapshots in PostgreSQL
- Store historical metrics in PostgreSQL
- Store detected whale signals in PostgreSQL

## Database Schema

### Tables

#### 1. watchlist_symbols
Stores symbols to monitor

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| symbol | VARCHAR(10) | Stock symbol (SPY, AAPL, etc.) |
| name | VARCHAR(100) | Company name |
| sector | VARCHAR(50) | Sector (Technology, Finance, etc.) |
| is_active | BOOLEAN | Active in watchlist? |
| added_date | TIMESTAMP | When added |
| notes | TEXT | Optional notes |

#### 2. option_contracts
Individual option contract snapshots

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| symbol | VARCHAR(10) | Underlying symbol |
| expiration | DATE | Expiration date |
| strike | NUMERIC | Strike price |
| right | CHAR(1) | 'C' = Call, 'P' = Put |
| volume | BIGINT | Today's volume |
| open_interest | BIGINT | Open interest |
| last_price | NUMERIC | Last trade price |
| implied_volatility | NUMERIC | IV |
| underlying_price | NUMERIC | Underlying price when scanned |
| timestamp | TIMESTAMP | When scanned |
| dte | INTEGER | Days to expiration |

#### 3. historical_metrics
Aggregated metrics per symbol per day

| Column | Type | Description |
|--------|------|-------------|
| symbol | VARCHAR(10) | Stock symbol |
| timestamp | TIMESTAMP | When recorded |
| total_call_volume | BIGINT | Total call volume |
| total_put_volume | BIGINT | Total put volume |
| pc_ratio_volume | NUMERIC | Put/Call ratio by volume |
| pc_ratio_oi | NUMERIC | Put/Call ratio by OI |
| avg_call_iv | NUMERIC | Average call IV |
| avg_put_iv | NUMERIC | Average put IV |
| iv_rank | NUMERIC | IV rank (0-100) |

#### 4. whale_signals
Detected whale trading signals

| Column | Type | Description |
|--------|------|-------------|
| symbol | VARCHAR(10) | Stock symbol |
| signal_type | VARCHAR(50) | Strong Bull, Institutional Hedge, etc. |
| signal_strength | INTEGER | 0-100 strength score |
| expiration | DATE | Option expiration |
| strike | NUMERIC | Strike price |
| volume | BIGINT | Volume that triggered signal |
| pc_ratio | NUMERIC | P/C ratio at detection |
| detected_at | TIMESTAMP | When detected |
| is_active | BOOLEAN | Still active? |

#### 5. scan_runs
Tracks each scanner execution

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| scan_date | TIMESTAMP | When scan ran |
| symbols_scanned | INTEGER | Number of symbols |
| total_contracts | INTEGER | Total option contracts scanned |
| signals_detected | INTEGER | Signals found |
| scan_duration_seconds | NUMERIC | How long scan took |

### Views

#### latest_metrics
Latest metrics for each symbol
```sql
SELECT * FROM latest_metrics;
```

#### active_whale_signals
Currently active whale signals
```sql
SELECT * FROM active_whale_signals;
```

#### top_volume_options_today
Top 100 volume options today
```sql
SELECT * FROM top_volume_options_today;
```

#### watchlist_with_metrics
Watchlist with latest metrics joined
```sql
SELECT * FROM watchlist_with_metrics;
```

## Usage Examples

### Manage Watchlist via Database

```bash
# Connect to database
psql -d whale_scanner

# View watchlist
SELECT symbol, name, sector FROM watchlist_symbols WHERE is_active = true;

# Add symbol
INSERT INTO watchlist_symbols (symbol, name, sector) VALUES ('GME', 'GameStop', 'Retail');

# Remove symbol (soft delete)
UPDATE watchlist_symbols SET is_active = false WHERE symbol = 'GME';

# Re-add symbol
UPDATE watchlist_symbols SET is_active = true WHERE symbol = 'GME';
```

### Query Historical Data

```sql
-- P/C ratio over last 30 days for SPY
SELECT timestamp, pc_ratio_volume, pc_ratio_oi
FROM historical_metrics
WHERE symbol = 'SPY'
  AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY timestamp;

-- Top 10 volume options today
SELECT symbol, strike, right, volume, open_interest
FROM option_contracts
WHERE DATE(timestamp) = CURRENT_DATE
ORDER BY volume DESC
LIMIT 10;

-- All Strong Bull signals last week
SELECT symbol, strike, detected_at, signal_strength
FROM whale_signals
WHERE signal_type = 'Strong Bull'
  AND detected_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY detected_at DESC;

-- Average scan duration
SELECT AVG(scan_duration_seconds) as avg_scan_time
FROM scan_runs
WHERE scan_date >= CURRENT_DATE - INTERVAL '7 days';
```

### Python API

```python
from postgres_storage import PostgresStorage
import yaml

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize storage
storage = PostgresStorage(config)

# Get watchlist
symbols = storage.get_watchlist()
print(f"Watchlist: {symbols}")

# Add symbol
storage.add_to_watchlist('NVDA', 'NVIDIA Corporation', 'Technology')

# Get active signals
signals = storage.get_active_signals(symbol='SPY', limit=10)
for signal in signals:
    print(f"{signal['symbol']}: {signal['signal_type']} - Strength {signal['signal_strength']}")

# Get historical metrics
import pandas as pd
metrics_df = storage.get_historical_metrics('SPY', days=30)
print(metrics_df[['timestamp', 'pc_ratio_volume', 'total_volume']])

# Close connection
storage.close()
```

## Data Visualization

### Connect Grafana

1. Install Grafana
2. Add PostgreSQL data source:
   - Host: localhost:5432
   - Database: whale_scanner
   - User: postgres

3. Create dashboards with queries like:
```sql
-- P/C Ratio Chart
SELECT
  time_bucket('1 hour', timestamp) AS time,
  symbol,
  AVG(pc_ratio_volume) as pc_ratio
FROM historical_metrics
WHERE symbol IN ('SPY', 'QQQ', 'AAPL')
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY time, symbol
ORDER BY time;
```

### Export to CSV

```bash
# Export watchlist
psql -d whale_scanner -c "COPY (SELECT * FROM watchlist_symbols) TO STDOUT WITH CSV HEADER" > watchlist.csv

# Export signals
psql -d whale_scanner -c "COPY (SELECT * FROM whale_signals WHERE detected_at >= CURRENT_DATE - INTERVAL '7 days') TO STDOUT WITH CSV HEADER" > signals.csv
```

## Troubleshooting

### Connection Refused

**Problem:** `psql: could not connect to server: Connection refused`

**Solution:**
```bash
# Check if PostgreSQL is running
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Start PostgreSQL
brew services start postgresql@16  # macOS
sudo systemctl start postgresql  # Linux
```

### Authentication Failed

**Problem:** `psql: FATAL: password authentication failed`

**Solution:**
```bash
# Reset postgres password (macOS/Linux)
psql postgres
ALTER USER postgres PASSWORD 'new_password';
\q

# Update config.yaml with new password
```

### Database Already Exists

When running setup script:
```
Database 'whale_scanner' already exists
Drop and recreate database? (yes/no):
```

Type `yes` to recreate (will delete all data) or `no` to keep existing database.

### Permission Denied

**Problem:** Cannot create database

**Solution:**
```bash
# Grant superuser privileges
psql postgres
ALTER USER postgres WITH SUPERUSER;
\q
```

## Performance Tips

### Indexes
The schema includes indexes on commonly queried columns. To add custom indexes:

```sql
-- Index for faster symbol+date queries
CREATE INDEX idx_contracts_symbol_timestamp ON option_contracts(symbol, timestamp DESC);

-- Index for volume queries
CREATE INDEX idx_contracts_high_volume ON option_contracts(volume DESC) WHERE volume > 10000;
```

### Partitioning
For large datasets, partition option_contracts by date:

```sql
-- Convert to partitioned table (advanced)
CREATE TABLE option_contracts_partitioned (
    LIKE option_contracts INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE option_contracts_2025_01 PARTITION OF option_contracts_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### Vacuum
Regular maintenance:

```sql
-- Vacuum to reclaim space and update stats
VACUUM ANALYZE;

-- Auto-vacuum is enabled by default in PostgreSQL
```

## Migration from SQLite

The scanner maintains SQLite compatibility. You can:

1. **Run both**: Keep SQLite for local storage, PostgreSQL for analytics
2. **Disable SQLite**: Set `storage.enable_historical_storage: false` in config.yaml
3. **Migrate data**: Export from SQLite, import to PostgreSQL (script TBD)

## Security

### Production Deployment

**Use environment variables for password:**

```yaml
postgres:
  password: ${POSTGRES_PASSWORD}  # Reads from environment variable
```

```bash
export POSTGRES_PASSWORD='your_secure_password'
python scanner.py
```

**Create dedicated user:**

```sql
CREATE USER whale_scanner WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE whale_scanner TO whale_scanner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO whale_scanner;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO whale_scanner;
```

Update config.yaml:
```yaml
postgres:
  user: "whale_scanner"  # Use dedicated user instead of postgres
```

## Backup

### Manual Backup

```bash
# Backup entire database
pg_dump whale_scanner > backup_$(date +%Y%m%d).sql

# Backup specific table
pg_dump -t whale_signals whale_scanner > signals_backup.sql
```

### Restore

```bash
# Restore database
psql whale_scanner < backup_20251104.sql

# Restore specific table
psql whale_scanner < signals_backup.sql
```

### Automated Backups

```bash
# Add to crontab (daily backup at 2 AM)
0 2 * * * pg_dump whale_scanner > /path/to/backups/whale_scanner_$(date +\%Y\%m\%d).sql
```

## Summary

| Feature | SQLite (Default) | PostgreSQL |
|---------|-----------------|------------|
| Setup | ✅ Automatic | ⚙️ Manual setup required |
| Concurrency | ⚠️ Limited | ✅ Excellent |
| Analytics | ⚠️ Basic queries | ✅ Advanced queries |
| Scalability | ⚠️ <10GB | ✅ Terabytes |
| Remote Access | ❌ No | ✅ Yes |
| Visualization | ❌ No | ✅ Grafana, Tableau |
| **Best For** | Quick start, testing | Production, analytics |

## Next Steps

1. **✅ Setup complete?** Run `python scanner.py` and watch data populate!
2. **📊 Want analytics?** Connect Grafana or Jupyter notebooks
3. **🔄 Need automation?** Set up cron jobs for scheduled scans
4. **📈 Backtesting?** Query historical_metrics for pattern analysis

Happy whale hunting with PostgreSQL! 🐋📊
