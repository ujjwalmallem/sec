"""
Database Storage Layer
PostgreSQL storage for whale scanner with clean API
"""

import os
import logging
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """
    PostgreSQL database storage for whale scanner

    Tables:
    - tickers: Watchlist symbols
    - whale_rules: Configurable detection rules
    - scan_runs: Scanner execution tracking
    - historical_metrics: Time-series metrics
    - option_contracts: Individual contract data
    - whale_signals: Detected whale signals
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database connection

        Args:
            connection_string: PostgreSQL connection string, or None to load from env
        """
        if connection_string is None:
            host = os.getenv('POSTGRES_HOST', 'localhost')
            port = os.getenv('POSTGRES_PORT', '5432')
            database = os.getenv('POSTGRES_DB', 'whale_scanner')
            user = os.getenv('POSTGRES_USER', 'whale_scanner')
            password = os.getenv('POSTGRES_PASSWORD', '')

            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        self.connection_string = connection_string

        try:
            # Create connection pool
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=connection_string
            )
            logger.info("Database connection pool created")

            # Test connection
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    version = cur.fetchone()[0]
                    logger.info(f"Connected to PostgreSQL: {version}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # ========================================================================
    # TICKERS
    # ========================================================================

    def get_active_tickers(self) -> List[Dict[str, Any]]:
        """Get all active tickers from watchlist"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM tickers
                    WHERE is_active = true
                    ORDER BY symbol
                """)
                return [dict(row) for row in cur.fetchall()]

    def add_ticker(self, symbol: str, name: Optional[str] = None,
                   sector: Optional[str] = None, notes: Optional[str] = None) -> int:
        """
        Add ticker to watchlist

        Args:
            symbol: Ticker symbol
            name: Company/ETF name
            sector: Sector classification
            notes: Additional notes

        Returns:
            Ticker ID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tickers (symbol, name, sector, notes, is_active)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (symbol) DO UPDATE
                    SET name = EXCLUDED.name,
                        sector = EXCLUDED.sector,
                        notes = EXCLUDED.notes,
                        is_active = true,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (symbol, name, sector, notes))
                return cur.fetchone()[0]

    def remove_ticker(self, symbol: str) -> bool:
        """
        Deactivate ticker from watchlist

        Args:
            symbol: Ticker symbol

        Returns:
            True if ticker was found and deactivated
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tickers
                    SET is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = %s
                """, (symbol,))
                return cur.rowcount > 0

    def get_ticker_id(self, symbol: str) -> Optional[int]:
        """Get ticker ID by symbol"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tickers WHERE symbol = %s", (symbol,))
                result = cur.fetchone()
                return result[0] if result else None

    # ========================================================================
    # WHALE RULES
    # ========================================================================

    def get_active_rules(self, rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active whale rules

        Args:
            rule_type: Filter by rule type ('FILTER', 'SIGNAL', 'COMBO'), or None for all

        Returns:
            List of active rules sorted by priority
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if rule_type:
                    cur.execute("""
                        SELECT * FROM whale_rules
                        WHERE is_active = true AND rule_type = %s
                        ORDER BY priority DESC, id
                    """, (rule_type,))
                else:
                    cur.execute("""
                        SELECT * FROM whale_rules
                        WHERE is_active = true
                        ORDER BY priority DESC, id
                    """)
                return [dict(row) for row in cur.fetchall()]

    def get_rule_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """Get rule by name"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM whale_rules WHERE rule_name = %s
                """, (rule_name,))
                row = cur.fetchone()
                return dict(row) if row else None

    def update_rule_config(self, rule_name: str, config: Dict[str, Any]) -> bool:
        """
        Update rule configuration

        Args:
            rule_name: Rule name
            config: New configuration dictionary

        Returns:
            True if rule was found and updated
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE whale_rules
                    SET rule_config = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE rule_name = %s
                """, (json.dumps(config), rule_name))
                return cur.rowcount > 0

    def toggle_rule(self, rule_name: str, is_active: bool) -> bool:
        """Enable or disable a rule"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE whale_rules
                    SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE rule_name = %s
                """, (is_active, rule_name))
                return cur.rowcount > 0

    # ========================================================================
    # SCAN RUNS
    # ========================================================================

    def create_scan_run(self, metadata: Optional[Dict] = None) -> int:
        """
        Create new scan run

        Args:
            metadata: Additional scan metadata

        Returns:
            Scan run ID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO scan_runs (status, metadata)
                    VALUES ('running', %s)
                    RETURNING id
                """, (json.dumps(metadata) if metadata else None,))
                return cur.fetchone()[0]

    def complete_scan_run(self, scan_id: int, symbols_scanned: int,
                         contracts_analyzed: int, signals_detected: int,
                         rules_applied: int, error: Optional[str] = None):
        """Complete scan run with statistics"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                status = 'failed' if error else 'completed'
                cur.execute("""
                    UPDATE scan_runs
                    SET completed_at = CURRENT_TIMESTAMP,
                        status = %s,
                        symbols_scanned = %s,
                        contracts_analyzed = %s,
                        signals_detected = %s,
                        rules_applied = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)),
                        error_message = %s
                    WHERE id = %s
                """, (status, symbols_scanned, contracts_analyzed, signals_detected,
                      rules_applied, error, scan_id))

    # ========================================================================
    # HISTORICAL METRICS
    # ========================================================================

    def save_metrics(self, symbol: str, metrics: Dict[str, Any],
                    scan_run_id: Optional[int] = None) -> int:
        """
        Save historical metrics for a symbol

        Args:
            symbol: Ticker symbol
            metrics: Dictionary of metric values
            scan_run_id: Associated scan run ID

        Returns:
            Metrics ID
        """
        ticker_id = self.get_ticker_id(symbol)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO historical_metrics (
                        ticker_id, symbol, timestamp,
                        underlying_price,
                        total_call_volume, total_put_volume, total_volume,
                        avg_10d_volume, avg_20d_volume,
                        total_call_oi, total_put_oi, total_oi,
                        call_oi_change, put_oi_change,
                        pc_ratio_volume, pc_ratio_oi,
                        avg_pc_10d, avg_pc_20d, stddev_pc,
                        avg_call_iv, avg_put_iv, iv_rank, iv_percentile,
                        put_call_iv_skew, price_change_pct, price_trend,
                        scan_run_id
                    ) VALUES (
                        %s, %s, CURRENT_TIMESTAMP,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (symbol, timestamp) DO UPDATE
                    SET underlying_price = EXCLUDED.underlying_price,
                        total_call_volume = EXCLUDED.total_call_volume,
                        total_put_volume = EXCLUDED.total_put_volume,
                        total_volume = EXCLUDED.total_volume,
                        avg_10d_volume = EXCLUDED.avg_10d_volume,
                        avg_20d_volume = EXCLUDED.avg_20d_volume,
                        total_call_oi = EXCLUDED.total_call_oi,
                        total_put_oi = EXCLUDED.total_put_oi,
                        total_oi = EXCLUDED.total_oi,
                        call_oi_change = EXCLUDED.call_oi_change,
                        put_oi_change = EXCLUDED.put_oi_change,
                        pc_ratio_volume = EXCLUDED.pc_ratio_volume,
                        pc_ratio_oi = EXCLUDED.pc_ratio_oi,
                        avg_pc_10d = EXCLUDED.avg_pc_10d,
                        avg_pc_20d = EXCLUDED.avg_pc_20d,
                        stddev_pc = EXCLUDED.stddev_pc,
                        avg_call_iv = EXCLUDED.avg_call_iv,
                        avg_put_iv = EXCLUDED.avg_put_iv,
                        iv_rank = EXCLUDED.iv_rank,
                        iv_percentile = EXCLUDED.iv_percentile,
                        put_call_iv_skew = EXCLUDED.put_call_iv_skew,
                        price_change_pct = EXCLUDED.price_change_pct,
                        price_trend = EXCLUDED.price_trend
                    RETURNING id
                """, (
                    ticker_id, symbol,
                    metrics.get('underlying_price'),
                    metrics.get('total_call_volume', 0),
                    metrics.get('total_put_volume', 0),
                    metrics.get('total_volume', 0),
                    metrics.get('avg_10d_volume'),
                    metrics.get('avg_20d_volume'),
                    metrics.get('total_call_oi', 0),
                    metrics.get('total_put_oi', 0),
                    metrics.get('total_oi', 0),
                    metrics.get('call_oi_change', 0),
                    metrics.get('put_oi_change', 0),
                    metrics.get('pc_ratio_volume'),
                    metrics.get('pc_ratio_oi'),
                    metrics.get('avg_pc_10d'),
                    metrics.get('avg_pc_20d'),
                    metrics.get('stddev_pc'),
                    metrics.get('avg_call_iv'),
                    metrics.get('avg_put_iv'),
                    metrics.get('iv_rank'),
                    metrics.get('iv_percentile'),
                    metrics.get('put_call_iv_skew'),
                    metrics.get('price_change_pct'),
                    metrics.get('price_trend'),
                    scan_run_id
                ))
                return cur.fetchone()[0]

    def get_historical_metrics(self, symbol: str, days: int = 20) -> List[Dict[str, Any]]:
        """Get historical metrics for calculating averages"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM historical_metrics
                    WHERE symbol = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (symbol, days))
                return [dict(row) for row in cur.fetchall()]

    # ========================================================================
    # OPTION CONTRACTS
    # ========================================================================

    def save_option_contract(self, contract: Dict[str, Any],
                            scan_run_id: Optional[int] = None) -> int:
        """Save option contract snapshot"""
        symbol = contract.get('underlying')
        ticker_id = self.get_ticker_id(symbol)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO option_contracts (
                        ticker_id, symbol, option_symbol,
                        expiration, strike, option_type, dte,
                        last_price, bid, ask, mid_price,
                        volume, open_interest, oi_change, volume_oi_ratio,
                        delta, gamma, theta, vega, implied_volatility,
                        underlying_price, moneyness, scan_run_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (option_symbol, timestamp) DO NOTHING
                    RETURNING id
                """, (
                    ticker_id,
                    symbol,
                    contract.get('symbol'),
                    contract.get('expiration_date'),
                    contract.get('strike'),
                    'C' if contract.get('option_type') == 'call' else 'P',
                    contract.get('dte'),
                    contract.get('last'),
                    contract.get('bid'),
                    contract.get('ask'),
                    contract.get('mid_price'),
                    contract.get('volume', 0),
                    contract.get('open_interest', 0),
                    contract.get('oi_change', 0),
                    contract.get('volume_oi_ratio'),
                    contract.get('greeks', {}).get('delta'),
                    contract.get('greeks', {}).get('gamma'),
                    contract.get('greeks', {}).get('theta'),
                    contract.get('greeks', {}).get('vega'),
                    contract.get('greeks', {}).get('mid_iv'),
                    contract.get('underlying_price'),
                    contract.get('moneyness'),
                    scan_run_id
                ))
                result = cur.fetchone()
                return result[0] if result else None

    # ========================================================================
    # WHALE SIGNALS
    # ========================================================================

    def save_signal(self, signal: Dict[str, Any], scan_run_id: Optional[int] = None) -> int:
        """
        Save detected whale signal

        Args:
            signal: Signal dictionary
            scan_run_id: Associated scan run ID

        Returns:
            Signal ID
        """
        symbol = signal.get('symbol')
        ticker_id = self.get_ticker_id(symbol)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO whale_signals (
                        ticker_id, symbol, signal_type, signal_strength,
                        rule_id, rule_name,
                        expiration, strike, option_type,
                        volume, open_interest, oi_change,
                        pc_ratio, iv_rank, volume_avg_ratio,
                        underlying_price, price_trend, description,
                        action_recommended, expires_at, is_active,
                        scan_run_id, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, true, %s, %s
                    )
                    RETURNING id
                """, (
                    ticker_id,
                    symbol,
                    signal.get('signal_type'),
                    signal.get('signal_strength', 50),
                    signal.get('rule_id'),
                    signal.get('rule_name'),
                    signal.get('expiration'),
                    signal.get('strike'),
                    signal.get('option_type'),
                    signal.get('volume'),
                    signal.get('open_interest'),
                    signal.get('oi_change'),
                    signal.get('pc_ratio'),
                    signal.get('iv_rank'),
                    signal.get('volume_avg_ratio'),
                    signal.get('underlying_price'),
                    signal.get('price_trend'),
                    signal.get('description'),
                    signal.get('action_recommended'),
                    signal.get('expires_at'),
                    scan_run_id,
                    json.dumps(signal.get('metadata')) if signal.get('metadata') else None
                ))
                return cur.fetchone()[0]

    def get_active_signals(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active whale signals"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if symbol:
                    cur.execute("""
                        SELECT * FROM active_signals
                        WHERE symbol = %s
                        ORDER BY detected_at DESC, signal_strength DESC
                    """, (symbol,))
                else:
                    cur.execute("""
                        SELECT * FROM active_signals
                        ORDER BY detected_at DESC, signal_strength DESC
                        LIMIT 100
                    """)
                return [dict(row) for row in cur.fetchall()]

    def deactivate_old_signals(self, hours: int = 24) -> int:
        """Deactivate signals older than specified hours"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE whale_signals
                    SET is_active = false
                    WHERE is_active = true
                    AND detected_at < CURRENT_TIMESTAMP - INTERVAL '%s hours'
                """, (hours,))
                return cur.rowcount

    # ========================================================================
    # DASHBOARD QUERIES
    # ========================================================================

    def get_watchlist_dashboard(self) -> List[Dict[str, Any]]:
        """Get watchlist with latest metrics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM watchlist_dashboard")
                return [dict(row) for row in cur.fetchall()]

    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scan runs"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM scan_runs
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]

    def close(self):
        """Close all database connections"""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("Database connections closed")


if __name__ == '__main__':
    # Test the storage layer
    logging.basicConfig(level=logging.INFO)

    db = DatabaseStorage()
    print("Database connection successful!")

    # Test ticker operations
    print("\nActive tickers:")
    tickers = db.get_active_tickers()
    for ticker in tickers[:5]:
        print(f"  {ticker['symbol']}: {ticker['name']}")

    # Test rule operations
    print("\nActive filter rules:")
    filters = db.get_active_rules('FILTER')
    for rule in filters[:3]:
        print(f"  {rule['rule_name']}: {rule['description']}")

    print("\nActive signal rules:")
    signals = db.get_active_rules('SIGNAL')
    for rule in signals[:3]:
        print(f"  {rule['rule_name']}: {rule['description']}")

    db.close()
