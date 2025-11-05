# Quick Start - Configuration Web UI

## Prerequisites Checklist

Before starting the web UI, ensure:

- [x] PostgreSQL installed
- [ ] PostgreSQL running
- [ ] Database initialized

## Step 1: Start PostgreSQL

### On macOS (Homebrew)

```bash
# Start PostgreSQL
brew services start postgresql@14
# or
brew services start postgresql

# Verify it's running
pg_isready
```

**Expected output:** `/tmp:5432 - accepting connections`

### On Linux

```bash
# Start PostgreSQL
sudo systemctl start postgresql
# or
sudo service postgresql start

# Verify it's running
pg_isready
```

### Check Status

```bash
pg_isready
```

If you see **"accepting connections"** - you're good to go! ✅

If you see **"no response"** or **"connection refused"** - PostgreSQL is not running ❌

## Step 2: Initialize Database (First Time Only)

```bash
cd /path/to/sec
python database/setup_postgres.py
```

This creates the `whale_scanner` database and all required tables.

## Step 3: Start Web UI

### Option A: Using the startup script (Recommended)

```bash
./start_config_ui.sh
```

This script checks PostgreSQL status and database before starting.

### Option B: Direct launch

```bash
python web_config_ui.py
```

## Step 4: Open Browser

Navigate to: **http://localhost:5000**

## Troubleshooting

### Error: "Connection refused"

**Problem:** PostgreSQL is not running

**Solution:**
```bash
# macOS
brew services start postgresql@14

# Linux
sudo systemctl start postgresql
```

### Error: "Database does not exist"

**Problem:** Database not initialized

**Solution:**
```bash
python database/setup_postgres.py
```

### Error: "Port 5000 already in use"

**Problem:** Another application using port 5000

**Solution 1:** Stop the other application
```bash
lsof -i :5000
kill -9 <PID>
```

**Solution 2:** Change port in `web_config_ui.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Use port 8080
```

### Socket.IO 404 Errors

**Problem:** Browser trying to connect to websockets

**Solution:** These errors are harmless and can be ignored. They occur because the browser expects socket.io but this is a traditional HTTP app.

## Common Commands

### Check PostgreSQL Status
```bash
pg_isready
```

### View Database Configs
```bash
python config_manager.py list
```

### Stop PostgreSQL
```bash
# macOS
brew services stop postgresql@14

# Linux
sudo systemctl stop postgresql
```

### View Web UI Logs

Web UI logs appear in the terminal where you ran the script. Look for:
- `INFO - Running on http://localhost:5000` - Server started successfully
- `ERROR - Failed to connect to PostgreSQL` - Database connection issue

## Quick Reference

| Action | Command |
|--------|---------|
| Start PostgreSQL | `brew services start postgresql@14` (macOS) |
| Check PostgreSQL | `pg_isready` |
| Initialize DB | `python database/setup_postgres.py` |
| Start Web UI | `./start_config_ui.sh` |
| Open Web UI | http://localhost:5000 |
| List configs | `python config_manager.py list` |

## What's Next?

Once the UI is running:

1. **Create your first profile**
   - Click "New Config"
   - Name it "aggressive"
   - Adjust thresholds lower for more signals

2. **Clone default profile**
   - Open "default" config
   - Click "Clone"
   - Experiment with the copy

3. **Compare profiles**
   - Click "Compare" in nav
   - Select two profiles
   - See all differences

4. **Activate profile**
   - Choose the profile you want to use
   - Click "Activate"
   - Scanner will use this configuration

## Need Help?

1. Check terminal output for error messages
2. Verify PostgreSQL is running: `pg_isready`
3. Check database exists: `psql -l | grep whale_scanner`
4. Review logs in terminal where web UI is running
