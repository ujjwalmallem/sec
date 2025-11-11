# Repository Structure

## Overview
IBKR Whale Options Scanner - Production-ready options flow analysis tool for detecting institutional trading activity.

## Deployment Methods

### Docker (Recommended)
- **Quick Start**: `./docker-start.sh`
- **Documentation**: `DOCKER_README.md`, `DOCKER_QUICKSTART.md`
- **Requirements**: Docker & Docker Compose only

### Traditional Setup
- **Quick Start**: `./setup.sh` then `./start_web.sh`
- **Documentation**: `README.md`, `QUICKSTART.md`
- **Requirements**: Python 3.8+, PostgreSQL (optional)

## Directory Structure

```
sec/
├── Core Application
│   ├── scanner.py                  # CLI scanner (main entry point)
│   ├── web_app.py                  # Web dashboard (Flask)
│   ├── web_config_ui.py            # Configuration UI (Flask)
│   └── config_manager.py           # Configuration management
│
├── Data Layer
│   ├── ibkr_connection.py          # IBKR TWS/Gateway API
│   ├── options_data.py             # IBKR options data fetcher
│   ├── tradier_connection.py       # Tradier REST API
│   ├── tradier_options_data.py     # Tradier options data fetcher
│   ├── data_storage.py             # SQLite storage (fallback)
│   └── postgres_storage.py         # PostgreSQL storage (primary)
│
├── Analysis Engine
│   ├── whale_filters.py            # Four-gate filtering system
│   ├── signal_detector.py          # Signal pattern detection
│   └── utils.py                    # Helper utilities
│
├── Docker Deployment
│   ├── Dockerfile                  # Multi-stage Docker build
│   ├── docker-compose.yml          # Service orchestration
│   ├── docker-start.sh             # Quick start script
│   ├── docker-stop.sh              # Stop script
│   ├── .dockerignore               # Build optimization
│   └── .env.example                # Environment template
│
├── Traditional Setup
│   ├── setup.sh                    # Python venv setup
│   ├── start_web.sh                # Start web UI (non-Docker)
│   ├── start_config_ui.sh          # Start config UI (non-Docker)
│   └── requirements.txt            # Python dependencies
│
├── Database
│   └── database/
│       └── schema.sql              # PostgreSQL schema
│
├── Frontend
│   ├── templates/                  # HTML templates
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   └── ...
│   └── static/                     # CSS, JS, images
│       ├── css/
│       └── js/
│
├── Configuration
│   ├── config.yaml                 # Application configuration
│   └── .env                        # Environment variables (not in git)
│
└── Documentation
    ├── README.md                   # Main documentation
    ├── DOCKER_README.md            # Docker deployment guide
    ├── DOCKER_QUICKSTART.md        # Docker quick start
    ├── QUICKSTART.md               # Traditional quick start
    ├── POSTGRES_SETUP.md           # PostgreSQL setup
    ├── DATABASE_CONFIG.md          # Configuration management
    ├── CONFIG_WEB_UI.md            # Config UI guide
    ├── TRADIER_SETUP.md            # Tradier API setup
    └── WEB_UI_README.md            # Web UI guide
```

## Key Files

### Entry Points
- `scanner.py` - CLI scanner for continuous/one-time scans
- `web_app.py` - Web dashboard (port 5000)
- `web_config_ui.py` - Configuration editor (port 5001)

### Configuration
- `.env` - Environment variables (create from `.env.example`)
- `config.yaml` - Application settings (YAML format)
- Database stores configuration profiles

### Data Providers
- **IBKR**: `ibkr_connection.py`, `options_data.py`
- **Tradier**: `tradier_connection.py`, `tradier_options_data.py`

### Storage
- **PostgreSQL** (production): `postgres_storage.py`
- **SQLite** (fallback): `data_storage.py`

## Runtime Directories

Created automatically:
- `data/` - Application data (gitignored)
- `logs/` - Application logs (gitignored)
- `venv/` - Python virtual environment (gitignored, non-Docker only)

## Docker Services

When running via Docker:
1. **postgres** - PostgreSQL database (port 5432)
2. **web-app** - Main dashboard (port 5000)
3. **config-ui** - Configuration UI (port 5001)
4. **scanner** - CLI scanner (optional, on-demand)

## Port Usage

- **5000** - Web dashboard
- **5001** - Configuration UI
- **5432** - PostgreSQL (Docker only)
- **7497** - IBKR TWS Paper Trading
- **7496** - IBKR TWS Live Trading

## Quick Commands

### Docker
```bash
# Start
./docker-start.sh

# View logs
docker-compose logs -f

# Stop
./docker-stop.sh
```

### Traditional
```bash
# Setup
./setup.sh
source venv/bin/activate

# Start web UI
./start_web.sh

# Start config UI
./start_config_ui.sh

# Run scanner
python scanner.py --continuous
```

## Environment Variables

See `.env.example` for full list. Key variables:

- `DATA_PROVIDER` - "ibkr" or "tradier"
- `POSTGRES_*` - Database credentials
- `TRADIER_*` - Tradier API settings
- `IBKR_*` - IBKR connection settings

## Documentation Index

1. **Getting Started**: `README.md` or `DOCKER_QUICKSTART.md`
2. **Docker Deployment**: `DOCKER_README.md`
3. **Configuration**: `DATABASE_CONFIG.md`, `CONFIG_WEB_UI.md`
4. **Data Providers**: `TRADIER_SETUP.md`
5. **Database**: `POSTGRES_SETUP.md`
6. **Web UI**: `WEB_UI_README.md`

## Development Status

✅ Production-ready
✅ Docker support
✅ Dual data provider support (IBKR + Tradier)
✅ PostgreSQL + SQLite support
✅ Web UI with real-time updates
✅ Configuration management system
✅ Comprehensive documentation

## License & Credits

IBKR Whale Options Scanner
For institutional options flow analysis
