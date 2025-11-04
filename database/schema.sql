-- Whale Options Scanner - PostgreSQL Database Schema
-- This schema stores watchlists and historical options data from Tradier API

-- Drop tables if they exist (for fresh setup)
DROP TABLE IF EXISTS option_contracts CASCADE;
DROP TABLE IF EXISTS historical_metrics CASCADE;
DROP TABLE IF EXISTS whale_signals CASCADE;
DROP TABLE IF EXISTS watchlist_symbols CASCADE;
DROP TABLE IF EXISTS scan_runs CASCADE;

-- Watchlist Symbols
CREATE TABLE watchlist_symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100),
    sector VARCHAR(50),
    industry VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    CONSTRAINT unique_symbol UNIQUE(symbol)
);

CREATE INDEX idx_watchlist_active ON watchlist_symbols(is_active);
CREATE INDEX idx_watchlist_symbol ON watchlist_symbols(symbol);

-- Scan Runs - Track each scan execution
CREATE TABLE scan_runs (
    id SERIAL PRIMARY KEY,
    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symbols_scanned INTEGER,
    total_contracts INTEGER,
    signals_detected INTEGER,
    scan_duration_seconds NUMERIC(10, 2),
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT
);

CREATE INDEX idx_scan_runs_date ON scan_runs(scan_date DESC);

-- Historical Metrics - Daily/hourly aggregated metrics
CREATE TABLE historical_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    underlying_price NUMERIC(10, 2),

    -- Volume metrics
    total_call_volume BIGINT DEFAULT 0,
    total_put_volume BIGINT DEFAULT 0,
    total_volume BIGINT DEFAULT 0,

    -- Open Interest metrics
    total_call_oi BIGINT DEFAULT 0,
    total_put_oi BIGINT DEFAULT 0,
    total_oi BIGINT DEFAULT 0,

    -- P/C Ratios
    pc_ratio_volume NUMERIC(10, 4),
    pc_ratio_oi NUMERIC(10, 4),

    -- IV metrics
    avg_call_iv NUMERIC(10, 4),
    avg_put_iv NUMERIC(10, 4),
    iv_rank NUMERIC(5, 2),

    -- Skew
    atm_skew NUMERIC(10, 4),

    -- Additional context
    scan_run_id INTEGER REFERENCES scan_runs(id),

    CONSTRAINT unique_symbol_timestamp UNIQUE(symbol, timestamp)
);

CREATE INDEX idx_metrics_symbol ON historical_metrics(symbol);
CREATE INDEX idx_metrics_timestamp ON historical_metrics(timestamp DESC);
CREATE INDEX idx_metrics_symbol_timestamp ON historical_metrics(symbol, timestamp DESC);

-- Option Contracts - Individual option contract data
CREATE TABLE option_contracts (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    expiration DATE NOT NULL,
    strike NUMERIC(10, 2) NOT NULL,
    right CHAR(1) NOT NULL CHECK (right IN ('C', 'P')),

    -- Pricing
    last_price NUMERIC(10, 4),
    bid NUMERIC(10, 4),
    ask NUMERIC(10, 4),

    -- Volume and OI
    volume BIGINT DEFAULT 0,
    open_interest BIGINT DEFAULT 0,

    -- Greeks
    delta NUMERIC(10, 6),
    gamma NUMERIC(10, 6),
    theta NUMERIC(10, 6),
    vega NUMERIC(10, 6),

    -- IV
    implied_volatility NUMERIC(10, 4),

    -- Underlying
    underlying_price NUMERIC(10, 2),

    -- Metadata
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dte INTEGER,
    moneyness NUMERIC(10, 4),
    scan_run_id INTEGER REFERENCES scan_runs(id),

    CONSTRAINT unique_contract_timestamp UNIQUE(symbol, expiration, strike, right, timestamp)
);

CREATE INDEX idx_contracts_symbol ON option_contracts(symbol);
CREATE INDEX idx_contracts_expiration ON option_contracts(expiration);
CREATE INDEX idx_contracts_timestamp ON option_contracts(timestamp DESC);
CREATE INDEX idx_contracts_symbol_exp ON option_contracts(symbol, expiration);
CREATE INDEX idx_contracts_volume ON option_contracts(volume DESC);
CREATE INDEX idx_contracts_oi ON option_contracts(open_interest DESC);

-- Whale Signals - Detected whale activity
CREATE TABLE whale_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    signal_strength INTEGER CHECK (signal_strength BETWEEN 0 AND 100),

    -- Signal details
    expiration DATE,
    strike NUMERIC(10, 2),
    right CHAR(1) CHECK (right IN ('C', 'P', 'B')), -- C=Call, P=Put, B=Both

    -- Metrics that triggered signal
    volume BIGINT,
    open_interest BIGINT,
    pc_ratio NUMERIC(10, 4),
    iv_rank NUMERIC(5, 2),

    -- Context
    underlying_price NUMERIC(10, 2),
    description TEXT,

    -- Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scan_run_id INTEGER REFERENCES scan_runs(id),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_signals_symbol ON whale_signals(symbol);
CREATE INDEX idx_signals_timestamp ON whale_signals(detected_at DESC);
CREATE INDEX idx_signals_type ON whale_signals(signal_type);
CREATE INDEX idx_signals_strength ON whale_signals(signal_strength DESC);
CREATE INDEX idx_signals_active ON whale_signals(is_active);

-- Views for common queries

-- Latest metrics for each symbol
CREATE OR REPLACE VIEW latest_metrics AS
SELECT DISTINCT ON (symbol)
    symbol,
    timestamp,
    underlying_price,
    total_volume,
    total_oi,
    pc_ratio_volume,
    pc_ratio_oi,
    avg_call_iv,
    avg_put_iv,
    iv_rank
FROM historical_metrics
ORDER BY symbol, timestamp DESC;

-- Active whale signals
CREATE OR REPLACE VIEW active_whale_signals AS
SELECT
    ws.*,
    hm.underlying_price as current_price,
    hm.pc_ratio_volume as current_pc_ratio
FROM whale_signals ws
LEFT JOIN latest_metrics hm ON ws.symbol = hm.symbol
WHERE ws.is_active = true
ORDER BY ws.detected_at DESC;

-- Top volume options today
CREATE OR REPLACE VIEW top_volume_options_today AS
SELECT
    symbol,
    expiration,
    strike,
    right,
    volume,
    open_interest,
    underlying_price,
    timestamp
FROM option_contracts
WHERE DATE(timestamp) = CURRENT_DATE
ORDER BY volume DESC
LIMIT 100;

-- Watchlist with latest metrics
CREATE OR REPLACE VIEW watchlist_with_metrics AS
SELECT
    ws.symbol,
    ws.name,
    ws.sector,
    ws.is_active,
    lm.underlying_price,
    lm.total_volume,
    lm.pc_ratio_volume,
    lm.iv_rank,
    lm.timestamp as last_updated
FROM watchlist_symbols ws
LEFT JOIN latest_metrics lm ON ws.symbol = lm.symbol
WHERE ws.is_active = true
ORDER BY ws.symbol;

-- Insert default watchlist
INSERT INTO watchlist_symbols (symbol, name, sector, is_active) VALUES
    ('SPY', 'SPDR S&P 500 ETF', 'ETF', true),
    ('QQQ', 'Invesco QQQ Trust', 'ETF', true),
    ('AAPL', 'Apple Inc.', 'Technology', true),
    ('NVDA', 'NVIDIA Corporation', 'Technology', true),
    ('TSLA', 'Tesla Inc.', 'Automotive', true),
    ('AMD', 'Advanced Micro Devices', 'Technology', true),
    ('MSFT', 'Microsoft Corporation', 'Technology', true),
    ('GOOGL', 'Alphabet Inc.', 'Technology', true),
    ('META', 'Meta Platforms Inc.', 'Technology', true),
    ('AMZN', 'Amazon.com Inc.', 'Technology', true)
ON CONFLICT (symbol) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE watchlist_symbols IS 'Stores symbols to monitor for whale activity';
COMMENT ON TABLE historical_metrics IS 'Aggregated daily/hourly metrics for each symbol';
COMMENT ON TABLE option_contracts IS 'Individual option contract snapshots';
COMMENT ON TABLE whale_signals IS 'Detected whale trading signals';
COMMENT ON TABLE scan_runs IS 'Tracks each scanner execution';

COMMENT ON COLUMN option_contracts.right IS 'C = Call, P = Put';
COMMENT ON COLUMN option_contracts.dte IS 'Days to expiration';
COMMENT ON COLUMN option_contracts.moneyness IS 'Percentage from ATM (positive = ITM for calls, negative = OTM for calls)';

-- Grant permissions (adjust username as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO whale_scanner;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO whale_scanner;

-- Success message
SELECT 'Database schema created successfully!' as status;
