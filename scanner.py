"""
Whale Options Scanner - Main Orchestrator
Coordinates all components to scan for whale options activity
"""

import logging
import time
import yaml
from datetime import datetime
from typing import Dict, List
import pandas as pd
from colorlog import ColoredFormatter

from ibkr_connection import get_ibkr_connection
from options_data import OptionsDataFetcher
from whale_filters import WhaleFilters
from signal_detector import SignalDetector
from data_storage import DataStorage


def setup_logging(config: dict):
    """Setup colored logging"""
    log_level = config['logging']['level']

    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s%(reset)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, log_level))

    # File handler if enabled
    if config['alerts']['enable_file_logging']:
        file_handler = logging.FileHandler(config['alerts']['log_file'])
        file_handler.setFormatter(logging.Formatter(config['logging']['format']))
        logger.addHandler(file_handler)

    # Filter out non-critical market data errors
    class MarketDataErrorFilter(logging.Filter):
        """Filter out Error 10091 (subscription errors that fall back to delayed data)"""
        def filter(self, record):
            if hasattr(record, 'getMessage'):
                msg = record.getMessage()
                if 'Error 10091' in msg or 'Part of requested market data requires additional subscription' in msg:
                    return False  # Suppress this non-critical error
            return True

    # Apply filter to ib_insync wrapper logger
    ib_wrapper_logger = logging.getLogger('ib_insync.wrapper')
    ib_wrapper_logger.addFilter(MarketDataErrorFilter())


class WhaleScanner:
    """Main whale options scanner"""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize whale scanner"""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup logging
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.logger.info("Initializing Whale Scanner...")

        self.ibkr = get_ibkr_connection(config_path)
        self.data_fetcher = OptionsDataFetcher(self.config)
        self.whale_filters = WhaleFilters(self.config)
        self.signal_detector = SignalDetector(self.config)
        self.data_storage = DataStorage(self.config)

        # Get watchlist
        self.watchlist = self.config['watchlist']['symbols']
        self.expirations = self.config['scanning']['expirations_to_scan']
        self.scan_interval = self.config['scanning']['interval_seconds']

        self.logger.info(f"✓ Initialized with watchlist: {', '.join(self.watchlist)}")

    def connect(self) -> bool:
        """Connect to IBKR"""
        return self.ibkr.connect()

    def scan_symbol(self, symbol: str) -> Dict:
        """
        Scan a single symbol for whale activity

        Args:
            symbol: Ticker symbol to scan

        Returns:
            Dictionary with scan results
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Scanning {symbol}...")
        self.logger.info(f"{'='*80}")

        try:
            # Fetch option chain data
            options_df = self.data_fetcher.get_option_chain_data(symbol, self.expirations)

            if options_df.empty:
                self.logger.warning(f"No option data found for {symbol}")
                return {'symbol': symbol, 'signals': [], 'data': None}

            # Get historical data for comparison
            historical_data = self.data_storage.get_historical_metrics(symbol)

            # Calculate current metrics
            current_metrics = self._calculate_current_metrics(options_df, symbol)

            # Store current data
            self.data_storage.store_metrics(symbol, current_metrics)

            # Apply whale filters
            filtered_df = self.whale_filters.apply_all_filters(options_df, historical_data)

            # Detect whale combo signals
            whale_combos = self.whale_filters.detect_whale_combos(filtered_df, historical_data)

            # Detect trading signals
            signals = self.signal_detector.detect_signals(
                filtered_df,
                symbol,
                historical_data,
                whale_combos
            )

            # Send alerts if signals found
            if signals:
                self.signal_detector.send_alerts(signals)

            return {
                'symbol': symbol,
                'signals': signals,
                'data': filtered_df,
                'metrics': current_metrics
            }

        except Exception as e:
            self.logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
            return {'symbol': symbol, 'signals': [], 'data': None}

    def _calculate_current_metrics(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Calculate current metrics for a symbol

        Args:
            df: Options DataFrame
            symbol: Ticker symbol

        Returns:
            Dictionary of metrics
        """
        try:
            # Calculate P/C ratio
            pc_ratio = self.data_fetcher.calculate_pc_ratio(df, by='volume')
            pc_ratio_oi = self.data_fetcher.calculate_pc_ratio(df, by='oi')

            # Get volume stats
            total_volume = df['volume'].sum()
            total_oi = df['open_interest'].sum()

            calls = df[df['right'] == 'C']
            puts = df[df['right'] == 'P']

            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            call_oi = calls['open_interest'].sum()
            put_oi = puts['open_interest'].sum()

            # Average IV
            avg_iv = df['implied_volatility'].mean()

            # Get underlying price
            underlying_price = df['underlying_price'].iloc[0] if not df.empty else 0

            metrics = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'underlying_price': underlying_price,
                'pc_ratio_volume': pc_ratio,
                'pc_ratio_oi': pc_ratio_oi,
                'total_volume': total_volume,
                'total_oi': total_oi,
                'call_volume': call_volume,
                'put_volume': put_volume,
                'call_oi': call_oi,
                'put_oi': put_oi,
                'avg_iv': avg_iv,
            }

            self.logger.info(f"\nCurrent Metrics for {symbol}:")
            self.logger.info(f"  Price: ${underlying_price:.2f}")
            self.logger.info(f"  P/C Ratio (Volume): {pc_ratio:.3f}")
            self.logger.info(f"  P/C Ratio (OI): {pc_ratio_oi:.3f}")
            self.logger.info(f"  Total Volume: {total_volume:,}")
            self.logger.info(f"  Total OI: {total_oi:,}")
            self.logger.info(f"  Avg IV: {avg_iv:.2%}" if avg_iv else "  Avg IV: N/A")

            return metrics

        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return {}

    def scan_all(self) -> Dict[str, List]:
        """
        Scan all symbols in watchlist

        Returns:
            Dictionary of symbol -> signals
        """
        all_results = {}

        for symbol in self.watchlist:
            result = self.scan_symbol(symbol)
            all_results[symbol] = result['signals']

            # Brief pause between symbols
            time.sleep(1)

        return all_results

    def run_continuous(self):
        """Run scanner continuously"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info("🐋 WHALE OPTIONS SCANNER - CONTINUOUS MODE")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Watchlist: {', '.join(self.watchlist)}")
        self.logger.info(f"Scan interval: {self.scan_interval} seconds")
        self.logger.info(f"{'='*80}\n")

        scan_count = 0

        try:
            while True:
                scan_count += 1
                start_time = time.time()

                self.logger.info(f"\n🔍 Scan #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Check if market is open
                if not self.ibkr.is_market_open():
                    self.logger.warning("⏸  Market is closed. Waiting...")
                    time.sleep(300)  # Wait 5 minutes
                    continue

                # Scan all symbols
                all_signals = self.scan_all()

                # Print summary
                self.signal_detector.print_summary(all_signals)

                # Calculate scan duration
                duration = time.time() - start_time
                self.logger.info(f"✓ Scan completed in {duration:.2f} seconds")

                # Keep connection alive
                self.ibkr.keep_alive()

                # Wait for next scan
                wait_time = max(0, self.scan_interval - duration)
                if wait_time > 0:
                    self.logger.info(f"⏳ Waiting {wait_time:.0f} seconds until next scan...")
                    time.sleep(wait_time)

        except KeyboardInterrupt:
            self.logger.info("\n\n⏹  Scanner stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in scanner: {e}", exc_info=True)
        finally:
            self.disconnect()

    def run_once(self):
        """Run scanner once and exit"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info("🐋 WHALE OPTIONS SCANNER - SINGLE SCAN")
        self.logger.info(f"{'='*80}\n")

        all_signals = self.scan_all()
        self.signal_detector.print_summary(all_signals)

        self.disconnect()

    def disconnect(self):
        """Disconnect from IBKR"""
        self.logger.info("\nDisconnecting from IBKR...")
        self.ibkr.disconnect()
        self.logger.info("✓ Disconnected")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='IBKR Whale Options Scanner')
    parser.add_argument(
        '--mode',
        choices=['continuous', 'once'],
        default='once',
        help='Scan mode: continuous or once (default: once)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Override watchlist with specific symbols'
    )

    args = parser.parse_args()

    # Create scanner
    scanner = WhaleScanner(args.config)

    # Override watchlist if specified
    if args.symbols:
        scanner.watchlist = args.symbols
        scanner.logger.info(f"Using custom watchlist: {', '.join(args.symbols)}")

    # Connect to IBKR
    if not scanner.connect():
        print("\n❌ Failed to connect to IBKR. Exiting.")
        print("\nTroubleshooting:")
        print("1. Make sure TWS or IB Gateway is running")
        print("2. Enable API connections: File → Global Configuration → API → Settings")
        print("3. Check that the port matches your config (7497 for paper, 7496 for live)")
        return

    # Run scanner
    if args.mode == 'continuous':
        scanner.run_continuous()
    else:
        scanner.run_once()


if __name__ == "__main__":
    main()
