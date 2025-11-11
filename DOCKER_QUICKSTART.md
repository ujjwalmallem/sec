# Docker Quick Start Guide

Get the IBKR Whale Options Scanner running with Docker in 5 minutes.

## Prerequisites

- Docker installed and running
- 2GB+ free RAM
- 10GB+ free disk space

## Quick Start

### 1. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings (required!)
nano .env
```

**Minimum required changes in `.env`:**
```env
# CHANGE THIS PASSWORD!
POSTGRES_PASSWORD=your_secure_password_here

# Choose your data provider
DATA_PROVIDER=tradier  # or 'ibkr'

# If using Tradier (no TWS needed):
TRADIER_API_KEY=your_api_key_here
TRADIER_ACCOUNT_ID=your_account_id_here

# If using IBKR (requires TWS/Gateway on host):
IBKR_HOST=host.docker.internal
IBKR_PORT=7497
```

### 2. Start Everything

```bash
# Quick start (web UI only)
./docker-start.sh

# OR start with scanner enabled
./docker-start.sh --with-scanner
```

### 3. Access the Application

- **Main Web UI**: http://localhost:8000
- **Config UI**: http://localhost:5001

## Common Commands

```bash
# View logs
docker-compose logs -f web-app

# Stop everything
./docker-stop.sh

# Restart
docker-compose restart

# Run a one-time scan
docker-compose run --rm scanner

# Remove everything (including data!)
./docker-stop.sh --clean
```

## Data Provider Setup

### Option A: Tradier (Recommended for Docker)
1. Get free API key: https://developer.tradier.com/
2. Set in `.env`:
   ```env
   DATA_PROVIDER=tradier
   TRADIER_API_KEY=your_key
   TRADIER_ACCOUNT_ID=your_account
   ```

### Option B: Interactive Brokers
1. Start TWS/Gateway on **host machine** (not in Docker)
2. Enable API in TWS: File > Global Configuration > API > Settings
3. Set in `.env`:
   ```env
   DATA_PROVIDER=ibkr
   IBKR_HOST=host.docker.internal
   IBKR_PORT=7497
   ```

## Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker info

# Check logs
docker-compose logs

# Rebuild everything
docker-compose build --no-cache
docker-compose up -d
```

### Port already in use
```bash
# Change ports in .env
WEB_PORT=5005
CONFIG_UI_PORT=5006

# Restart
docker-compose down
docker-compose up -d
```

### Database issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

## Next Steps

- Configure watchlist via Web UI: http://localhost:8000
- Adjust scanner settings: http://localhost:5001
- View full documentation: [DOCKER_README.md](DOCKER_README.md)

## Getting Help

- Full Docker Guide: `DOCKER_README.md`
- Main Documentation: `README.md`
- Database Setup: `POSTGRES_SETUP.md`
- Configuration: `DATABASE_CONFIG.md`
