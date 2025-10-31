"""
Data Storage Module
Stores and retrieves historical options data for whale detection
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class DataStorage:
    """Handles storage and retrieval of historical options data"""

    def __init__(self, config: dict):
        """Initialize data storage"""
        self.config = config
        self.db_path = config['storage']['database_path']
        self.enable_storage = config['storage']['enable_historical_storage']
        self.retention_days = config['storage']['retention_days']

        # Create database directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        if self.enable_storage:
            self._init_database()

    def _init_database(self):
        """Initialize SQLite database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Metrics table - stores daily metrics per symbol
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    underlying_price REAL,
                    pc_ratio_volume REAL,
                    pc_ratio_oi REAL,
                    total_volume INTEGER,
                    total_oi INTEGER,
                    call_volume INTEGER,
                    put_volume INTEGER,
                    call_oi INTEGER,
                    put_oi INTEGER,
                    avg_iv REAL,
                    data_json TEXT
                )
            ''')

            # Signals table - stores detected whale signals
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT,
                    action TEXT,
                    strike REAL,
                    expiration TEXT,
                    dte INTEGER,
                    right TEXT,
                    volume INTEGER,
                    open_interest INTEGER,
                    implied_volatility REAL,
                    signal_strength INTEGER,
                    data_json TEXT
                )
            ''')

            # Option contracts table - stores individual option data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS option_contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    expiration TEXT,
                    strike REAL,
                    right TEXT,
                    volume INTEGER,
                    open_interest INTEGER,
                    oi_change INTEGER,
                    implied_volatility REAL,
                    delta REAL,
                    gamma REAL,
                    theta REAL,
                    vega REAL,
                    last REAL,
                    bid REAL,
                    ask REAL
                )
            ''')

            # Create indexes for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_symbol_timestamp
                ON metrics(symbol, timestamp)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp
                ON signals(symbol, timestamp)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_contracts_symbol_timestamp
                ON option_contracts(symbol, timestamp)
            ''')

            conn.commit()
            conn.close()

            logger.info(f"✓ Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def store_metrics(self, symbol: str, metrics: Dict):
        """
        Store metrics for a symbol

        Args:
            symbol: Ticker symbol
            metrics: Dictionary of metrics
        """
        if not self.enable_storage:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO metrics (
                    timestamp, symbol, underlying_price, pc_ratio_volume, pc_ratio_oi,
                    total_volume, total_oi, call_volume, put_volume, call_oi, put_oi,
                    avg_iv, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.get('timestamp', datetime.now().isoformat()),
                symbol,
                metrics.get('underlying_price'),
                metrics.get('pc_ratio_volume'),
                metrics.get('pc_ratio_oi'),
                metrics.get('total_volume'),
                metrics.get('total_oi'),
                metrics.get('call_volume'),
                metrics.get('put_volume'),
                metrics.get('call_oi'),
                metrics.get('put_oi'),
                metrics.get('avg_iv'),
                json.dumps(metrics)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing metrics: {e}")

    def store_signal(self, signal: Dict):
        """
        Store a detected signal

        Args:
            signal: Signal dictionary
        """
        if not self.enable_storage:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO signals (
                    timestamp, symbol, signal_type, action, strike, expiration,
                    dte, right, volume, open_interest, implied_volatility,
                    signal_strength, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.get('timestamp', datetime.now().isoformat()),
                signal['symbol'],
                signal.get('type'),
                signal.get('action'),
                signal.get('strike'),
                signal.get('expiration'),
                signal.get('dte'),
                signal.get('right'),
                signal.get('volume'),
                signal.get('open_interest'),
                signal.get('implied_volatility'),
                signal.get('signal_strength'),
                json.dumps(signal)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing signal: {e}")

    def get_historical_metrics(self, symbol: str, days: int = 20) -> Dict:
        """
        Get historical metrics for a symbol

        Args:
            symbol: Ticker symbol
            days: Number of days to retrieve

        Returns:
            Dictionary with historical metrics
        """
        if not self.enable_storage:
            return self._get_default_historical_data()

        try:
            conn = sqlite3.connect(self.db_path)

            # Get metrics from last N days
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            query = '''
                SELECT * FROM metrics
                WHERE symbol = ? AND timestamp > ?
                ORDER BY timestamp ASC
            '''

            df = pd.read_sql_query(query, conn, params=(symbol, cutoff_date))
            conn.close()

            if df.empty:
                return self._get_default_historical_data()

            # Extract time series data
            historical = {
                'pc_ratios': df['pc_ratio_volume'].tolist(),
                'pc_ratios_oi': df['pc_ratio_oi'].tolist(),
                'volumes': df['total_volume'].tolist(),
                'avg_volume_10d': df['total_volume'].tail(10).mean(),
                'avg_volume_20d': df['total_volume'].mean(),
                'iv_history': df['avg_iv'].dropna().tolist(),
                'oi_history': df['total_oi'].tolist(),
            }

            return historical

        except Exception as e:
            logger.error(f"Error retrieving historical metrics: {e}")
            return self._get_default_historical_data()

    def _get_default_historical_data(self) -> Dict:
        """Get default historical data when no data available"""
        return {
            'pc_ratios': [],
            'pc_ratios_oi': [],
            'volumes': [],
            'avg_volume_10d': 0,
            'avg_volume_20d': 0,
            'iv_history': [],
            'oi_history': [],
        }

    def get_recent_signals(self, symbol: Optional[str] = None, days: int = 7) -> pd.DataFrame:
        """
        Get recent signals

        Args:
            symbol: Ticker symbol (None for all symbols)
            days: Number of days to retrieve

        Returns:
            DataFrame with signals
        """
        if not self.enable_storage:
            return pd.DataFrame()

        try:
            conn = sqlite3.connect(self.db_path)
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            if symbol:
                query = '''
                    SELECT * FROM signals
                    WHERE symbol = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                '''
                df = pd.read_sql_query(query, conn, params=(symbol, cutoff_date))
            else:
                query = '''
                    SELECT * FROM signals
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                '''
                df = pd.read_sql_query(query, conn, params=(cutoff_date,))

            conn.close()
            return df

        except Exception as e:
            logger.error(f"Error retrieving recent signals: {e}")
            return pd.DataFrame()

    def cleanup_old_data(self):
        """Clean up data older than retention period"""
        if not self.enable_storage:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=self.retention_days)).isoformat()

            # Delete old metrics
            cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_date,))
            metrics_deleted = cursor.rowcount

            # Delete old signals
            cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff_date,))
            signals_deleted = cursor.rowcount

            # Delete old contracts
            cursor.execute('DELETE FROM option_contracts WHERE timestamp < ?', (cutoff_date,))
            contracts_deleted = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(
                f"Cleaned up old data: {metrics_deleted} metrics, "
                f"{signals_deleted} signals, {contracts_deleted} contracts"
            )

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        if not self.enable_storage:
            return {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}

            # Count metrics
            cursor.execute('SELECT COUNT(*) FROM metrics')
            stats['total_metrics'] = cursor.fetchone()[0]

            # Count signals
            cursor.execute('SELECT COUNT(*) FROM signals')
            stats['total_signals'] = cursor.fetchone()[0]

            # Count unique symbols
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM metrics')
            stats['unique_symbols'] = cursor.fetchone()[0]

            # Get date range
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM metrics')
            date_range = cursor.fetchone()
            stats['date_range'] = date_range

            conn.close()

            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
