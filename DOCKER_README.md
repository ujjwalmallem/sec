# Docker Deployment Guide - IBKR Whale Options Scanner

This guide explains how to run the IBKR Whale Options Scanner using Docker and Docker Compose.

## Overview

The Docker setup includes:
- **PostgreSQL Database** - Persistent storage for watchlists, configurations, and historical data
- **Web Application** - Main dashboard with real-time signal monitoring (Port 5000)
- **Configuration UI** - Web interface for managing scanner settings (Port 5001)
- **Scanner Service** - Optional CLI scanner for continuous monitoring

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or docker-compose 1.29+)
- At least 2GB free RAM
- 10GB free disk space (for database and logs)

## Quick Start

### 1. Initial Setup

```bash
# Clone the repository (if not already done)
cd /path/to/ibkr-whale-scanner

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
nano .env  # or vim, code, etc.
```

### 2. Configure Environment

Edit `.env` file with your configuration:

**Required Settings:**
```env
# Change the default password!
POSTGRES_PASSWORD=your_secure_password_here

# Choose data provider: 'ibkr' or 'tradier'
DATA_PROVIDER=tradier

# If using Tradier (no TWS needed):
TRADIER_API_KEY=your_tradier_api_key
TRADIER_ACCOUNT_ID=your_tradier_account_id

# If using IBKR (requires TWS/Gateway running on host):
IBKR_HOST=host.docker.internal
IBKR_PORT=7497  # 7497=paper, 7496=live
IBKR_CLIENT_ID=1
```

### 3. Start Services

**Option A: Using helper script (recommended)**
```bash
./docker-start.sh
```

**Option B: Using docker-compose directly**
```bash
docker-compose up -d
```

**Option C: Start with scanner enabled**
```bash
./docker-start.sh --with-scanner
# Or:
docker-compose --profile scanner up -d
```

### 4. Access the Application

- **Main Web UI**: http://localhost:5000
- **Configuration UI**: http://localhost:5001
- **PostgreSQL**: localhost:5432

## Service Architecture

```
┌─────────────────────────────────────────────┐
│          Host Machine (Your Computer)       │
│  ┌────────────────────────────────────────┐ │
│  │         Docker Network                 │ │
│  │                                        │ │
│  │  ┌──────────┐  ┌──────────┐          │ │
│  │  │ Web App  │  │ Config   │          │ │
│  │  │  :5000   │  │ UI :5001 │          │ │
│  │  └────┬─────┘  └────┬─────┘          │ │
│  │       │             │                 │ │
│  │       └──────┬──────┘                 │ │
│  │              │                        │ │
│  │      ┌───────▼────────┐              │ │
│  │      │   PostgreSQL   │              │ │
│  │      │     :5432      │              │ │
│  │      └────────────────┘              │ │
│  │                                       │ │
│  │  ┌────────────────┐  (optional)      │ │
│  │  │    Scanner     │                  │ │
│  │  │  (CLI mode)    │                  │ │
│  │  └────────────────┘                  │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ┌─────────────────┐  (if using IBKR)      │
│  │   TWS/Gateway   │                       │
│  │     :7497       │                       │
│  └─────────────────┘                       │
└─────────────────────────────────────────────┘
```

## Docker Services

### 1. PostgreSQL Database (`postgres`)
- **Purpose**: Persistent data storage
- **Port**: 5432
- **Volume**: `postgres_data` (persistent)
- **Health Check**: Automatic readiness probe

### 2. Web Application (`web-app`)
- **Purpose**: Main dashboard and real-time monitoring
- **Port**: 5000
- **Command**: `python web_app.py`
- **Depends On**: PostgreSQL
- **Volumes**:
  - `./data:/app/data` - Local data files
  - `./logs:/app/logs` - Application logs

### 3. Configuration UI (`config-ui`)
- **Purpose**: Web-based configuration management
- **Port**: 5001
- **Command**: `python web_config_ui.py`
- **Depends On**: PostgreSQL

### 4. Scanner Service (`scanner`)
- **Purpose**: CLI-based continuous scanning
- **Profile**: `scanner` (optional service)
- **Command**: `python scanner.py --continuous --interval 60`
- **Start With**: `docker-compose --profile scanner up -d`

## Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web-app
docker-compose logs -f postgres
docker-compose logs -f config-ui

# Last 100 lines
docker-compose logs --tail=100 web-app
```

### Check Service Status

```bash
docker-compose ps
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart web-app
```

### Stop Services

```bash
# Using helper script
./docker-stop.sh

# Using docker-compose
docker-compose down

# Stop and remove volumes (DELETES ALL DATA)
./docker-stop.sh --clean
# Or:
docker-compose down -v
```

### Run Scanner Manually

```bash
# One-time scan
docker-compose run --rm scanner python scanner.py

# Continuous scanning (60 second interval)
docker-compose run --rm scanner python scanner.py --continuous --interval 60
```

### Access Database

```bash
# Using psql from host (if installed)
psql -h localhost -p 5432 -U whale_scanner -d whale_scanner

# Using Docker exec
docker exec -it whale-scanner-db psql -U whale_scanner -d whale_scanner

# Example queries
docker exec -it whale-scanner-db psql -U whale_scanner -d whale_scanner -c "SELECT * FROM watchlist_symbols;"
```

### Execute Commands in Container

```bash
# Access web-app shell
docker exec -it whale-scanner-web bash

# Run Python script
docker exec -it whale-scanner-web python scanner.py --help
```

## Data Persistence

### Volumes

```bash
# List volumes
docker volume ls

# Inspect postgres volume
docker volume inspect sec_postgres_data

# Backup database
docker exec whale-scanner-db pg_dump -U whale_scanner whale_scanner > backup.sql

# Restore database
docker exec -i whale-scanner-db psql -U whale_scanner whale_scanner < backup.sql
```

### Local Directories

The following directories are mounted as volumes:
- `./data/` - Application data files (watchlists, configs)
- `./logs/` - Application log files

## Configuration

### Environment Variables

All configuration is done via `.env` file. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | change_this_password |
| `DATA_PROVIDER` | Data source (ibkr/tradier) | tradier |
| `TRADIER_API_KEY` | Tradier API key | - |
| `IBKR_HOST` | IBKR TWS host | host.docker.internal |
| `IBKR_PORT` | IBKR TWS port | 7497 |
| `WEB_PORT` | Web UI port | 5000 |
| `CONFIG_UI_PORT` | Config UI port | 5001 |

### Using IBKR with Docker

If using Interactive Brokers:

1. Start TWS or IB Gateway on your **host machine**
2. Configure TWS to accept connections:
   - File > Global Configuration > API > Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Socket port: 7497 (paper) or 7496 (live)
   - Add "127.0.0.1" to trusted IPs
3. Set in `.env`:
   ```env
   DATA_PROVIDER=ibkr
   IBKR_HOST=host.docker.internal
   IBKR_PORT=7497
   ```

**Note**: `host.docker.internal` allows Docker containers to connect to services running on the host machine.

### Using Tradier with Docker

If using Tradier (no TWS needed):

1. Get API credentials from https://developer.tradier.com/
2. Set in `.env`:
   ```env
   DATA_PROVIDER=tradier
   TRADIER_API_KEY=your_key_here
   TRADIER_ACCOUNT_ID=your_account_id_here
   ```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# Check logs for errors
docker-compose logs

# Rebuild images
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Failed

```bash
# Check PostgreSQL is healthy
docker-compose ps

# Check database logs
docker-compose logs postgres

# Verify connection settings in .env
cat .env | grep POSTGRES
```

### Can't Connect to IBKR TWS

1. Verify TWS/Gateway is running on host
2. Check IBKR settings allow API connections
3. Verify port in `.env` matches TWS (7497 or 7496)
4. Check logs: `docker-compose logs web-app`

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :5000
sudo lsof -i :5432

# Change port in .env
WEB_PORT=5005
POSTGRES_PORT=5433

# Restart
docker-compose down
docker-compose up -d
```

### Reset Everything

```bash
# Stop and remove all containers, networks, volumes
./docker-stop.sh --clean

# Remove images
docker-compose down --rmi all

# Start fresh
./docker-start.sh
```

## Production Deployment

### Security Best Practices

1. **Change default password**:
   ```env
   POSTGRES_PASSWORD=use_strong_random_password_here
   ```

2. **Use secrets management** (for production):
   ```bash
   # Instead of .env, use Docker secrets
   echo "my_db_password" | docker secret create postgres_password -
   ```

3. **Restrict ports** (optional):
   ```yaml
   # In docker-compose.yml, bind to localhost only:
   ports:
     - "127.0.0.1:5432:5432"
   ```

4. **Enable HTTPS** (use reverse proxy like nginx or traefik)

### Performance Tuning

For production workloads, adjust PostgreSQL settings:

```yaml
# In docker-compose.yml, add to postgres environment:
environment:
  POSTGRES_SHARED_BUFFERS: 256MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
  POSTGRES_MAX_CONNECTIONS: 100
```

### Monitoring

```bash
# Resource usage
docker stats

# Disk usage
docker system df

# Database size
docker exec whale-scanner-db psql -U whale_scanner -c "SELECT pg_size_pretty(pg_database_size('whale_scanner'));"
```

## Updating

```bash
# Pull latest changes
git pull

# Rebuild images
docker-compose build

# Restart with new images
docker-compose up -d

# View updated services
docker-compose ps
```

## Uninstallation

```bash
# Stop and remove everything
docker-compose down -v --rmi all

# Remove directories (optional)
rm -rf data/ logs/

# Remove scripts
rm docker-start.sh docker-stop.sh .env
```

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review main documentation: `README.md`
- Check configuration: `DATABASE_CONFIG.md`
- PostgreSQL setup: `POSTGRES_SETUP.md`

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Main Project README](README.md)
