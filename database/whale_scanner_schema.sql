-- ============================================================================
-- WHALE SCANNER - PostgreSQL Database Schema (Redesigned from Scratch)
-- ============================================================================
-- Stores tickers, configurable whale rules, signals, and metrics
-- Designed for Tradier API integration

-- Drop existing tables
DROP TABLE IF EXISTS whale_signals CASCADE;
DROP TABLE IF EXISTS option_contracts CASCADE;
DROP TABLE IF EXISTS historical_metrics CASCADE;
DROP TABLE IF EXISTS scan_runs CASCADE;
DROP TABLE IF EXISTS whale_rules CASCADE;
DROP TABLE IF EXISTS tickers CASCADE;

-- ============================================================================
-- TICKERS - Watchlist of symbols to monitor
-- ============================================================================
CREATE TABLE tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100),
    sector VARCHAR(50),
    market_cap BIGINT,
    is_active BOOLEAN DEFAULT true,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    CONSTRAINT unique_ticker_symbol UNIQUE(symbol)
);

CREATE INDEX idx_tickers_active ON tickers(is_active);
CREATE INDEX idx_tickers_symbol ON tickers(symbol);
CREATE INDEX idx_tickers_sector ON tickers(sector);

-- Insert default watchlist
INSERT INTO tickers (symbol, name, sector, is_active) VALUES
    ('SPY', 'SPDR S&P 500 ETF', 'ETF', true),
    ('QQQ', 'Invesco QQQ Trust', 'ETF', true),
    ('IWM', 'iShares Russell 2000 ETF', 'ETF', true),
    ('AAPL', 'Apple Inc.', 'Technology', true),
    ('NVDA', 'NVIDIA Corporation', 'Technology', true),
    ('TSLA', 'Tesla Inc.', 'Automotive', true),
    ('AMD', 'Advanced Micro Devices', 'Technology', true),
    ('MSFT', 'Microsoft Corporation', 'Technology', true),
    ('GOOGL', 'Alphabet Inc.', 'Technology', true),
    ('META', 'Meta Platforms Inc.', 'Technology', true),
    ('AMZN', 'Amazon.com Inc.', 'Technology', true),
    ('NFLX', 'Netflix Inc.', 'Technology', true)
ON CONFLICT (symbol) DO NOTHING;

-- ============================================================================
-- WHALE RULES - Configurable whale detection rules
-- ============================================================================
CREATE TABLE whale_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL, -- 'FILTER', 'SIGNAL', 'COMBO'
    description TEXT,
    rule_config JSONB NOT NULL,
    priority INTEGER DEFAULT 0, -- Higher priority rules checked first
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_rule_name UNIQUE(rule_name)
);

CREATE INDEX idx_whale_rules_type ON whale_rules(rule_type);
CREATE INDEX idx_whale_rules_active ON whale_rules(is_active);
CREATE INDEX idx_whale_rules_priority ON whale_rules(priority DESC);
CREATE INDEX idx_whale_rules_config ON whale_rules USING gin(rule_config);

-- Insert whale rules based on provided logic
INSERT INTO whale_rules (rule_name, rule_type, description, rule_config, priority, is_active) VALUES

-- CORE FILTERS (Gates 1-4) - RELAXED FOR TESTING
('liquidity_gate', 'FILTER', 'Gate 1: Liquidity filter - Volume and OI thresholds',
 '{"min_volume": 1000, "min_oi": 500, "min_oi_per_strike": 10}'::jsonb, 100, true),

('anomaly_gate', 'FILTER', 'Gate 2: P/C ratio anomaly detection',
 '{"pc_deviation_threshold": 0.3, "pc_lookback_days": 20, "pc_bullish_threshold": 0.7, "pc_bearish_threshold": 1.3, "pc_extreme_low": 0.3, "pc_extreme_high": 1.5}'::jsonb, 90, true),

('conviction_gate', 'FILTER', 'Gate 3: Volume vs OI conviction filter',
 '{"volume_vs_avg_multiplier": 1.1, "oi_growth_required": false, "oi_delta_min": 50, "volume_vs_10d_avg": 1.2}'::jsonb, 80, true),

('volatility_gate', 'FILTER', 'Gate 4: IV Rank extremes',
 '{"ivr_expensive": 60, "ivr_cheap": 40, "ivr_extreme_high": 70, "ivr_extreme_low": 30, "ivr_lookback_days": 252}'::jsonb, 70, true),

-- BASIC FILTERS - RELAXED
('volume_greater_than_oi', 'FILTER', 'Volume must exceed Open Interest',
 '{"enabled": false}'::jsonb, 60, true),

('min_oi_threshold', 'FILTER', 'Minimum OI requirement',
 '{"min_oi": 100}'::jsonb, 50, true),

('pc_ratio_extreme', 'FILTER', 'P/C ratio <= 0.3 (extreme bullish)',
 '{"max_pc_ratio": 2.0}'::jsonb, 40, true),

-- SIGNAL DETECTION RULES - RELAXED
('strong_bull_signal', 'SIGNAL', 'Strong bullish: Low P/C + High call vol + Rising call OI + Low IVR',
 '{"pc_ratio_max": 1.2, "call_volume_min_multiplier": 1.2, "call_oi_increasing": false, "ivr_max": 60}'::jsonb, 95, true),

('institutional_hedge', 'SIGNAL', 'Crash protection: High P/C + Put spike + Rising put OI + High IVR',
 '{"pc_ratio_min": 0.8, "put_volume_spike_multiplier": 1.5, "put_oi_increasing": false, "ivr_min": 40}'::jsonb, 94, true),

('retail_fomo', 'SIGNAL', 'Retail FOMO: P/C <0.3 + Volume 5x avg + No OI change (FADE)',
 '{"pc_ratio_max": 2.0, "volume_multiplier": 1.5, "oi_change_max": 50000, "fade_signal": true}'::jsonb, 85, true),

-- COMBO SIGNALS - RELAXED
('whale_conviction', 'COMBO', 'High conviction whale: Volume >2x avg + P/C deviation + OI delta + IV extreme',
 '{"volume_multiplier": 1.2, "pc_deviation_sigma": 0.3, "oi_delta_min": 100, "ivr_extreme": false}'::jsonb, 98, true),

('custom_scanner', 'COMBO', 'Custom scanner: Volume spike + P/C anomaly + OI change + IV extremes',
 '{"volume_vs_20d_avg": 1.2, "pc_deviation_sigma": 0.3, "oi_change_min": 100, "ivr_high": 60, "ivr_low": 40}'::jsonb, 97, true),

-- OI PATTERN RULES - RELAXED
('smart_money_long', 'SIGNAL', 'OI ↑ in Calls + Price ↑ = Smart money long',
 '{"call_oi_increasing": true, "price_trend": "up", "action": "FOLLOW"}'::jsonb, 88, true),

('hedging_pattern', 'SIGNAL', 'OI ↑ in Puts + Price ↑ = Hedging (not bearish)',
 '{"put_oi_increasing": true, "price_trend": "up", "action": "IGNORE"}'::jsonb, 87, true),

('short_squeeze_fuel', 'SIGNAL', 'OI ↓ in Puts + Price ↓ = Put covering, short squeeze fuel',
 '{"put_oi_decreasing": true, "price_trend": "down", "action": "BUY_CALLS"}'::jsonb, 86, true),

-- IV RULES - RELAXED
('iv_crush_opportunity', 'SIGNAL', 'Sell premium when IVR >90 pre-event',
 '{"ivr_min": 60, "action": "SELL_PREMIUM", "dte_max": 30}'::jsonb, 75, true),

('cheap_volatility', 'SIGNAL', 'Buy calendars when IVR <10',
 '{"ivr_max": 40, "action": "BUY_CALENDARS"}'::jsonb, 74, true);

-- ============================================================================
-- SCAN RUNS - Track each scanner execution
-- ============================================================================
CREATE TABLE scan_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'failed'
    symbols_scanned INTEGER DEFAULT 0,
    contracts_analyzed INTEGER DEFAULT 0,
    signals_detected INTEGER DEFAULT 0,
    rules_applied INTEGER DEFAULT 0,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    metadata JSONB -- Store additional scan info
);

CREATE INDEX idx_scan_runs_status ON scan_runs(status);
CREATE INDEX idx_scan_runs_started ON scan_runs(started_at DESC);

-- ============================================================================
-- HISTORICAL METRICS - Time-series data for each symbol
-- ============================================================================
CREATE TABLE historical_metrics (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER REFERENCES tickers(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    underlying_price NUMERIC(12, 4),

    -- Volume metrics
    total_call_volume BIGINT DEFAULT 0,
    total_put_volume BIGINT DEFAULT 0,
    total_volume BIGINT DEFAULT 0,
    avg_10d_volume BIGINT,
    avg_20d_volume BIGINT,

    -- Open Interest metrics
    total_call_oi BIGINT DEFAULT 0,
    total_put_oi BIGINT DEFAULT 0,
    total_oi BIGINT DEFAULT 0,
    call_oi_change BIGINT DEFAULT 0,
    put_oi_change BIGINT DEFAULT 0,

    -- P/C Ratios
    pc_ratio_volume NUMERIC(10, 4),
    pc_ratio_oi NUMERIC(10, 4),
    avg_pc_10d NUMERIC(10, 4),
    avg_pc_20d NUMERIC(10, 4),
    stddev_pc NUMERIC(10, 4),

    -- IV metrics
    avg_call_iv NUMERIC(10, 4),
    avg_put_iv NUMERIC(10, 4),
    iv_rank NUMERIC(5, 2),
    iv_percentile NUMERIC(5, 2),
    put_call_iv_skew NUMERIC(10, 4),

    -- Price action
    price_change_pct NUMERIC(10, 4),
    price_trend VARCHAR(10), -- 'up', 'down', 'flat'

    scan_run_id INTEGER REFERENCES scan_runs(id),

    CONSTRAINT unique_symbol_timestamp UNIQUE(symbol, timestamp)
);

CREATE INDEX idx_metrics_symbol ON historical_metrics(symbol);
CREATE INDEX idx_metrics_timestamp ON historical_metrics(timestamp DESC);
CREATE INDEX idx_metrics_symbol_time ON historical_metrics(symbol, timestamp DESC);
CREATE INDEX idx_metrics_ticker ON historical_metrics(ticker_id);
CREATE INDEX idx_metrics_iv_rank ON historical_metrics(iv_rank);
CREATE INDEX idx_metrics_pc_ratio ON historical_metrics(pc_ratio_volume);

-- ============================================================================
-- OPTION CONTRACTS - Individual option contract snapshots
-- ============================================================================
CREATE TABLE option_contracts (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER REFERENCES tickers(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,

    -- Contract details
    expiration DATE NOT NULL,
    strike NUMERIC(12, 2) NOT NULL,
    option_type CHAR(1) NOT NULL CHECK (option_type IN ('C', 'P')),
    dte INTEGER, -- Days to expiration

    -- Pricing
    last_price NUMERIC(12, 4),
    bid NUMERIC(12, 4),
    ask NUMERIC(12, 4),
    mid_price NUMERIC(12, 4),

    -- Volume and OI
    volume BIGINT DEFAULT 0,
    open_interest BIGINT DEFAULT 0,
    oi_change INTEGER DEFAULT 0,
    volume_oi_ratio NUMERIC(10, 4),

    -- Greeks
    delta NUMERIC(10, 6),
    gamma NUMERIC(10, 6),
    theta NUMERIC(10, 6),
    vega NUMERIC(10, 6),

    -- IV
    implied_volatility NUMERIC(10, 4),

    -- Underlying
    underlying_price NUMERIC(12, 4),
    moneyness NUMERIC(10, 4), -- Distance from ATM

    -- Metadata
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scan_run_id INTEGER REFERENCES scan_runs(id),

    CONSTRAINT unique_contract_snapshot UNIQUE(option_symbol, timestamp)
);

CREATE INDEX idx_contracts_symbol ON option_contracts(symbol);
CREATE INDEX idx_contracts_option_symbol ON option_contracts(option_symbol);
CREATE INDEX idx_contracts_expiration ON option_contracts(expiration);
CREATE INDEX idx_contracts_timestamp ON option_contracts(timestamp DESC);
CREATE INDEX idx_contracts_volume ON option_contracts(volume DESC);
CREATE INDEX idx_contracts_oi ON option_contracts(open_interest DESC);
CREATE INDEX idx_contracts_type ON option_contracts(option_type);
CREATE INDEX idx_contracts_dte ON option_contracts(dte);

-- ============================================================================
-- WHALE SIGNALS - Detected whale activity based on rules
-- ============================================================================
CREATE TABLE whale_signals (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER REFERENCES tickers(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,

    -- Signal identification
    signal_type VARCHAR(50) NOT NULL,
    signal_strength INTEGER CHECK (signal_strength BETWEEN 0 AND 100),
    rule_id INTEGER REFERENCES whale_rules(id),
    rule_name VARCHAR(100),

    -- Signal details
    expiration DATE,
    strike NUMERIC(12, 2),
    option_type CHAR(1) CHECK (option_type IN ('C', 'P', 'B')), -- C=Call, P=Put, B=Both

    -- Metrics that triggered signal
    volume BIGINT,
    open_interest BIGINT,
    oi_change INTEGER,
    pc_ratio NUMERIC(10, 4),
    iv_rank NUMERIC(5, 2),
    volume_avg_ratio NUMERIC(10, 4),

    -- Context
    underlying_price NUMERIC(12, 4),
    price_trend VARCHAR(10),
    description TEXT,
    action_recommended VARCHAR(50), -- 'FOLLOW', 'FADE', 'IGNORE', 'BUY_CALLS', 'SELL_PREMIUM', etc.

    -- Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- When signal becomes stale
    is_active BOOLEAN DEFAULT true,
    scan_run_id INTEGER REFERENCES scan_runs(id),
    metadata JSONB -- Additional signal data
);

CREATE INDEX idx_signals_symbol ON whale_signals(symbol);
CREATE INDEX idx_signals_type ON whale_signals(signal_type);
CREATE INDEX idx_signals_detected ON whale_signals(detected_at DESC);
CREATE INDEX idx_signals_strength ON whale_signals(signal_strength DESC);
CREATE INDEX idx_signals_active ON whale_signals(is_active);
CREATE INDEX idx_signals_action ON whale_signals(action_recommended);
CREATE INDEX idx_signals_rule ON whale_signals(rule_id);

-- ============================================================================
-- VIEWS - Convenient queries
-- ============================================================================

-- Latest metrics for each symbol
CREATE OR REPLACE VIEW latest_metrics AS
SELECT DISTINCT ON (symbol)
    m.*,
    t.name as ticker_name,
    t.sector
FROM historical_metrics m
JOIN tickers t ON m.ticker_id = t.id
WHERE t.is_active = true
ORDER BY symbol, timestamp DESC;

-- Active whale signals with context
CREATE OR REPLACE VIEW active_signals AS
SELECT
    ws.*,
    t.name as ticker_name,
    t.sector,
    lm.underlying_price as current_price,
    lm.pc_ratio_volume as current_pc_ratio,
    lm.iv_rank as current_iv_rank,
    wr.description as rule_description
FROM whale_signals ws
JOIN tickers t ON ws.ticker_id = t.id
LEFT JOIN latest_metrics lm ON ws.symbol = lm.symbol
LEFT JOIN whale_rules wr ON ws.rule_id = wr.id
WHERE ws.is_active = true
  AND (ws.expires_at IS NULL OR ws.expires_at > CURRENT_TIMESTAMP)
ORDER BY ws.detected_at DESC, ws.signal_strength DESC;

-- Top volume options today
CREATE OR REPLACE VIEW top_volume_today AS
SELECT
    symbol,
    option_symbol,
    expiration,
    strike,
    option_type,
    volume,
    open_interest,
    volume_oi_ratio,
    underlying_price,
    implied_volatility,
    timestamp
FROM option_contracts
WHERE DATE(timestamp) = CURRENT_DATE
  AND volume > 0
ORDER BY volume DESC
LIMIT 100;

-- Watchlist with latest metrics
CREATE OR REPLACE VIEW watchlist_dashboard AS
SELECT
    t.id,
    t.symbol,
    t.name,
    t.sector,
    t.is_active,
    lm.underlying_price,
    lm.total_volume,
    lm.avg_20d_volume,
    lm.pc_ratio_volume,
    lm.pc_ratio_oi,
    lm.iv_rank,
    lm.put_call_iv_skew,
    lm.timestamp as last_updated,
    (SELECT COUNT(*) FROM whale_signals WHERE ticker_id = t.id AND is_active = true) as active_signals
FROM tickers t
LEFT JOIN latest_metrics lm ON t.symbol = lm.symbol
WHERE t.is_active = true
ORDER BY t.symbol;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update ticker updated_at timestamp
CREATE OR REPLACE FUNCTION update_ticker_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_ticker_timestamp
BEFORE UPDATE ON tickers
FOR EACH ROW
EXECUTE FUNCTION update_ticker_timestamp();

-- Function to update whale_rules updated_at timestamp
CREATE OR REPLACE FUNCTION update_rule_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_rule_timestamp
BEFORE UPDATE ON whale_rules
FOR EACH ROW
EXECUTE FUNCTION update_rule_timestamp();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE tickers IS 'Watchlist of symbols to monitor for whale activity';
COMMENT ON TABLE whale_rules IS 'Configurable whale detection rules stored as JSONB';
COMMENT ON TABLE scan_runs IS 'Tracks each scanner execution run';
COMMENT ON TABLE historical_metrics IS 'Time-series aggregated metrics for each symbol';
COMMENT ON TABLE option_contracts IS 'Individual option contract snapshots from Tradier';
COMMENT ON TABLE whale_signals IS 'Detected whale signals based on rule evaluation';

COMMENT ON COLUMN whale_rules.rule_config IS 'JSONB configuration for rule parameters';
COMMENT ON COLUMN whale_signals.action_recommended IS 'Trading action: FOLLOW, FADE, IGNORE, BUY_CALLS, SELL_PREMIUM, etc.';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
SELECT 'Database schema created successfully! Whale rules loaded.' as status;
