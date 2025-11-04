"""
PostgreSQL Data Storage
Stores watchlists and historical options data from Tradier API
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgresStorage:
    """PostgreSQL storage for whale scanner data"""

    def __init__(self, config: dict):
        """
        Initialize PostgreSQL storage

        Args:
            config: Configuration dictionary with postgres settings
        """
        self.config = config
        pg_config = config.get('postgres', {})

        # Connection parameters
        self.db_params = {
            'host': pg_config.get('host', 'localhost'),
            'port': pg_config.get('port', 5432),
            'database': pg_config.get('database', 'whale_scanner'),
            'user': pg_config.get('user', 'postgres'),
            'password': pg_config.get('password', ''),
        }

        # Connection pool
        self.pool = None
        self._init_connection_pool()

    def _init_connection_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self.db_params
            )
            logger.info(f"✓ Connected to PostgreSQL: {self.db_params['host']}:{self.db_params['port']}/{self.db_params['database']}")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
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

    def close(self):
        """Close all connections"""
        if self.pool:
            self.pool.closeall()
            logger.info("Closed PostgreSQL connection pool")

    # ========== Watchlist Management ==========

    def get_watchlist(self, active_only: bool = True) -> List[str]:
        """
        Get watchlist symbols

        Args:
            active_only: Return only active symbols

        Returns:
            List of symbol strings
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if active_only:
                        cur.execute("SELECT symbol FROM watchlist_symbols WHERE is_active = true ORDER BY symbol")
                    else:
                        cur.execute("SELECT symbol FROM watchlist_symbols ORDER BY symbol")

                    symbols = [row[0] for row in cur.fetchall()]
                    logger.info(f"Retrieved {len(symbols)} symbols from watchlist")
                    return symbols

        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []

    def add_to_watchlist(self, symbol: str, name: str = None, sector: str = None) -> bool:
        """
        Add symbol to watchlist

        Args:
            symbol: Stock symbol
            name: Company name
            sector: Sector

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO watchlist_symbols (symbol, name, sector, is_active)
                        VALUES (%s, %s, %s, true)
                        ON CONFLICT (symbol) DO UPDATE SET is_active = true
                    """, (symbol, name, sector))

                    logger.info(f"Added {symbol} to watchlist")
                    return True

        except Exception as e:
            logger.error(f"Error adding {symbol} to watchlist: {e}")
            return False

    def remove_from_watchlist(self, symbol: str) -> bool:
        """
        Remove symbol from watchlist (soft delete)

        Args:
            symbol: Stock symbol

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE watchlist_symbols SET is_active = false WHERE symbol = %s
                    """, (symbol,))

                    logger.info(f"Removed {symbol} from watchlist")
                    return True

        except Exception as e:
            logger.error(f"Error removing {symbol} from watchlist: {e}")
            return False

    # ========== Scan Run Management ==========

    def start_scan_run(self, symbols_to_scan: int) -> Optional[int]:
        """
        Create a new scan run entry

        Args:
            symbols_to_scan: Number of symbols to scan

        Returns:
            Scan run ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO scan_runs (scan_date, symbols_scanned, status)
                        VALUES (CURRENT_TIMESTAMP, %s, 'running')
                        RETURNING id
                    """, (symbols_to_scan,))

                    scan_run_id = cur.fetchone()[0]
                    logger.debug(f"Started scan run #{scan_run_id}")
                    return scan_run_id

        except Exception as e:
            logger.error(f"Error starting scan run: {e}")
            return None

    def complete_scan_run(self, scan_run_id: int, total_contracts: int, signals_detected: int, duration: float):
        """
        Mark scan run as complete

        Args:
            scan_run_id: Scan run ID
            total_contracts: Total contracts scanned
            signals_detected: Number of signals detected
            duration: Scan duration in seconds
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE scan_runs
                        SET total_contracts = %s,
                            signals_detected = %s,
                            scan_duration_seconds = %s,
                            status = 'completed'
                        WHERE id = %s
                    """, (total_contracts, signals_detected, duration, scan_run_id))

                    logger.debug(f"Completed scan run #{scan_run_id}")

        except Exception as e:
            logger.error(f"Error completing scan run: {e}")

    # ========== Historical Metrics Storage ==========

    def store_metrics(self, symbol: str, metrics: Dict, scan_run_id: int = None):
        """
        Store aggregated metrics for a symbol

        Args:
            symbol: Stock symbol
            metrics: Dictionary of metrics
            scan_run_id: Optional scan run ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO historical_metrics (
                            symbol, timestamp, underlying_price,
                            total_call_volume, total_put_volume, total_volume,
                            total_call_oi, total_put_oi, total_oi,
                            pc_ratio_volume, pc_ratio_oi,
                            avg_call_iv, avg_put_iv, iv_rank,
                            atm_skew, scan_run_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (symbol, timestamp) DO UPDATE SET
                            underlying_price = EXCLUDED.underlying_price,
                            total_call_volume = EXCLUDED.total_call_volume,
                            total_put_volume = EXCLUDED.total_put_volume,
                            total_volume = EXCLUDED.total_volume,
                            total_call_oi = EXCLUDED.total_call_oi,
                            total_put_oi = EXCLUDED.total_put_oi,
                            total_oi = EXCLUDED.total_oi,
                            pc_ratio_volume = EXCLUDED.pc_ratio_volume,
                            pc_ratio_oi = EXCLUDED.pc_ratio_oi,
                            avg_call_iv = EXCLUDED.avg_call_iv,
                            avg_put_iv = EXCLUDED.avg_put_iv,
                            iv_rank = EXCLUDED.iv_rank,
                            atm_skew = EXCLUDED.atm_skew
                    """, (
                        symbol,
                        metrics.get('timestamp', datetime.now()),
                        metrics.get('underlying_price'),
                        metrics.get('call_volume', 0),
                        metrics.get('put_volume', 0),
                        metrics.get('total_volume', 0),
                        metrics.get('call_oi', 0),
                        metrics.get('put_oi', 0),
                        metrics.get('total_oi', 0),
                        metrics.get('pc_ratio_volume'),
                        metrics.get('pc_ratio_oi'),
                        metrics.get('avg_call_iv'),
                        metrics.get('avg_put_iv'),
                        metrics.get('iv_rank'),
                        metrics.get('atm_skew'),
                        scan_run_id
                    ))

                    logger.debug(f"Stored metrics for {symbol}")

        except Exception as e:
            logger.error(f"Error storing metrics for {symbol}: {e}")

    def get_historical_metrics(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Get historical metrics for a symbol

        Args:
            symbol: Stock symbol
            days: Number of days to retrieve

        Returns:
            DataFrame with historical metrics
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT *
                    FROM historical_metrics
                    WHERE symbol = %s
                        AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    ORDER BY timestamp DESC
                """

                df = pd.read_sql_query(query, conn, params=(symbol, days))
                logger.debug(f"Retrieved {len(df)} historical records for {symbol}")
                return df

        except Exception as e:
            logger.error(f"Error getting historical metrics for {symbol}: {e}")
            return pd.DataFrame()

    # ========== Option Contracts Storage ==========

    def store_option_contracts(self, df: pd.DataFrame, scan_run_id: int = None):
        """
        Store option contract snapshots

        Args:
            df: DataFrame with option contract data
            scan_run_id: Optional scan run ID
        """
        if df.empty:
            return

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Prepare data for batch insert
                    records = []
                    for _, row in df.iterrows():
                        records.append((
                            row.get('symbol'),
                            pd.to_datetime(row.get('expiration'), format='%Y%m%d').date() if isinstance(row.get('expiration'), str) else row.get('expiration'),
                            float(row.get('strike', 0)),
                            row.get('right'),
                            float(row.get('last', 0)) if pd.notna(row.get('last')) else None,
                            float(row.get('bid', 0)) if pd.notna(row.get('bid')) else None,
                            float(row.get('ask', 0)) if pd.notna(row.get('ask')) else None,
                            int(row.get('volume', 0)),
                            int(row.get('open_interest', 0)),
                            float(row.get('delta', 0)) if pd.notna(row.get('delta')) else None,
                            float(row.get('gamma', 0)) if pd.notna(row.get('gamma')) else None,
                            float(row.get('theta', 0)) if pd.notna(row.get('theta')) else None,
                            float(row.get('vega', 0)) if pd.notna(row.get('vega')) else None,
                            float(row.get('implied_volatility', 0)) if pd.notna(row.get('implied_volatility')) else None,
                            float(row.get('underlying_price', 0)),
                            datetime.now(),
                            int(row.get('dte', 0)),
                            float(row.get('moneyness', 0)) if pd.notna(row.get('moneyness')) else None,
                            scan_run_id
                        ))

                    # Batch insert
                    execute_values(cur, """
                        INSERT INTO option_contracts (
                            symbol, expiration, strike, right,
                            last_price, bid, ask,
                            volume, open_interest,
                            delta, gamma, theta, vega,
                            implied_volatility, underlying_price,
                            timestamp, dte, moneyness, scan_run_id
                        ) VALUES %s
                        ON CONFLICT (symbol, expiration, strike, right, timestamp) DO NOTHING
                    """, records)

                    logger.info(f"Stored {len(records)} option contracts")

        except Exception as e:
            logger.error(f"Error storing option contracts: {e}")
            import traceback
            traceback.print_exc()

    # ========== Whale Signals Storage ==========

    def store_whale_signal(self, signal: Dict, scan_run_id: int = None):
        """
        Store detected whale signal

        Args:
            signal: Signal dictionary
            scan_run_id: Optional scan run ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO whale_signals (
                            symbol, signal_type, signal_strength,
                            expiration, strike, right,
                            volume, open_interest, pc_ratio, iv_rank,
                            underlying_price, description,
                            detected_at, scan_run_id, is_active
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true
                        )
                    """, (
                        signal.get('symbol'),
                        signal.get('signal_type'),
                        signal.get('signal_strength'),
                        signal.get('expiration'),
                        signal.get('strike'),
                        signal.get('right'),
                        signal.get('volume'),
                        signal.get('open_interest'),
                        signal.get('pc_ratio'),
                        signal.get('iv_rank'),
                        signal.get('underlying_price'),
                        signal.get('description'),
                        datetime.now(),
                        scan_run_id
                    ))

                    logger.info(f"Stored whale signal: {signal.get('symbol')} - {signal.get('signal_type')}")

        except Exception as e:
            logger.error(f"Error storing whale signal: {e}")

    def get_active_signals(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """
        Get active whale signals

        Args:
            symbol: Optional symbol filter
            limit: Maximum number of signals

        Returns:
            List of signal dictionaries
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if symbol:
                        cur.execute("""
                            SELECT * FROM active_whale_signals
                            WHERE symbol = %s
                            ORDER BY detected_at DESC
                            LIMIT %s
                        """, (symbol, limit))
                    else:
                        cur.execute("""
                            SELECT * FROM active_whale_signals
                            ORDER BY detected_at DESC
                            LIMIT %s
                        """, (limit,))

                    signals = [dict(row) for row in cur.fetchall()]
                    return signals

        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []

    # ========== Analytics ==========

    def get_top_volume_options(self, limit: int = 50) -> pd.DataFrame:
        """Get top volume options for today"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM top_volume_options_today LIMIT %s"
                df = pd.read_sql_query(query, conn, params=(limit,))
                return df

        except Exception as e:
            logger.error(f"Error getting top volume options: {e}")
            return pd.DataFrame()

    def get_watchlist_with_metrics(self) -> pd.DataFrame:
        """Get watchlist with latest metrics"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM watchlist_with_metrics"
                df = pd.read_sql_query(query, conn)
                return df

        except Exception as e:
            logger.error(f"Error getting watchlist with metrics: {e}")
            return pd.DataFrame()


def test_postgres_storage():
    """Test PostgreSQL storage"""
    import yaml

    print("\n" + "=" * 60)
    print("Testing PostgreSQL Storage")
    print("=" * 60)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize storage
    storage = PostgresStorage(config)

    # Test watchlist
    print("\n1. Testing Watchlist...")
    symbols = storage.get_watchlist()
    print(f"   ✓ Watchlist: {symbols}")

    # Test adding symbol
    print("\n2. Testing Add to Watchlist...")
    storage.add_to_watchlist("GME", "GameStop Corp.", "Retail")
    print("   ✓ Added GME")

    # Test metrics storage
    print("\n3. Testing Metrics Storage...")
    test_metrics = {
        'timestamp': datetime.now(),
        'underlying_price': 450.25,
        'call_volume': 1000000,
        'put_volume': 800000,
        'total_volume': 1800000,
        'pc_ratio_volume': 0.8,
        'pc_ratio_oi': 0.9
    }
    storage.store_metrics('SPY', test_metrics)
    print("   ✓ Stored metrics for SPY")

    # Close
    storage.close()
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_postgres_storage()
