"""
Whale Scanner
Live options flow scanner using Tradier API and configurable rules
"""

import os
import logging
import time
import statistics
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, date
from dataclasses import dataclass

from tradier_client import TradierClient, TradierConfig
from database_storage import DatabaseStorage
from rule_engine import WhaleRuleEngine, RuleEvaluationResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ScannerConfig:
    """Scanner configuration"""
    scan_interval: int = 60  # seconds between scans
    max_expirations: int = 5  # number of expirations to scan per symbol
    calculate_iv_rank_days: int = 252  # trading days for IV rank calculation
    historical_lookback_days: int = 20  # days for averages
    signal_expiry_hours: int = 24  # hours until signal expires


class WhaleScanner:
    """
    Live whale options scanner

    Workflow:
    1. Fetch active tickers from database
    2. Get options data from Tradier for each ticker
    3. Calculate metrics (volume, OI, P/C ratios, IV)
    4. Load active whale rules from database
    5. Evaluate rules via rule engine
    6. Save detected signals to database
    7. Sleep and repeat
    """

    def __init__(self, tradier_client: Optional[TradierClient] = None,
                 database: Optional[DatabaseStorage] = None,
                 config: Optional[ScannerConfig] = None):
        """
        Initialize whale scanner

        Args:
            tradier_client: Tradier API client (or None to create from env)
            database: Database storage (or None to create from env)
            config: Scanner configuration
        """
        self.tradier = tradier_client or TradierClient()
        self.db = database or DatabaseStorage()
        self.config = config or ScannerConfig()

        self.running = False

        logger.info(f"Whale scanner initialized")
        logger.info(f"  Scan interval: {self.config.scan_interval}s")
        logger.info(f"  Max expirations: {self.config.max_expirations}")

    def run_once(self) -> Dict[str, Any]:
        """
        Run scanner once

        Returns:
            Dictionary with scan statistics
        """
        logger.info("=" * 80)
        logger.info("Starting whale scan...")
        logger.info("=" * 80)

        start_time = time.time()

        # Create scan run record
        scan_id = self.db.create_scan_run({'mode': 'single'})

        try:
            # Get active tickers
            tickers = self.db.get_active_tickers()
            logger.info(f"Scanning {len(tickers)} tickers")

            # Load active rules
            rules = self.db.get_active_rules()
            logger.info(f"Loaded {len(rules)} active rules")

            # Initialize rule engine
            rule_engine = WhaleRuleEngine(rules)

            # Scan each ticker
            total_contracts = 0
            total_signals = 0

            for ticker in tickers:
                symbol = ticker['symbol']
                logger.info(f"\n--- Scanning {symbol} ---")

                try:
                    # Scan this ticker
                    contracts, signals = self._scan_ticker(symbol, rule_engine, scan_id)
                    total_contracts += contracts
                    total_signals += signals

                    logger.info(f"{symbol}: {contracts} contracts, {signals} signals")

                    # Rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
                    continue

            # Complete scan run
            duration = time.time() - start_time
            self.db.complete_scan_run(
                scan_id=scan_id,
                symbols_scanned=len(tickers),
                contracts_analyzed=total_contracts,
                signals_detected=total_signals,
                rules_applied=len(rules)
            )

            # Deactivate old signals
            deactivated = self.db.deactivate_old_signals(hours=self.config.signal_expiry_hours)

            logger.info("=" * 80)
            logger.info(f"Scan complete in {duration:.1f}s")
            logger.info(f"  Symbols: {len(tickers)}")
            logger.info(f"  Contracts: {total_contracts:,}")
            logger.info(f"  Signals: {total_signals}")
            logger.info(f"  Deactivated: {deactivated} old signals")
            logger.info("=" * 80)

            return {
                'scan_id': scan_id,
                'symbols_scanned': len(tickers),
                'contracts_analyzed': total_contracts,
                'signals_detected': total_signals,
                'duration_seconds': duration,
                'status': 'completed'
            }

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self.db.complete_scan_run(
                scan_id=scan_id,
                symbols_scanned=0,
                contracts_analyzed=0,
                signals_detected=0,
                rules_applied=0,
                error=str(e)
            )
            raise

    def run_continuous(self):
        """Run scanner continuously"""
        self.running = True
        logger.info(f"Starting continuous scanner (interval: {self.config.scan_interval}s)")
        logger.info("Press Ctrl+C to stop")

        try:
            while self.running:
                try:
                    self.run_once()
                except Exception as e:
                    logger.error(f"Scan error: {e}")

                # Sleep between scans
                logger.info(f"\nSleeping for {self.config.scan_interval} seconds...")
                time.sleep(self.config.scan_interval)

        except KeyboardInterrupt:
            logger.info("\nScanner stopped by user")
            self.running = False

    def stop(self):
        """Stop continuous scanner"""
        self.running = False

    def _scan_ticker(self, symbol: str, rule_engine: WhaleRuleEngine,
                    scan_id: int) -> tuple[int, int]:
        """
        Scan a single ticker

        Args:
            symbol: Ticker symbol
            rule_engine: Rule engine for evaluation
            scan_id: Scan run ID

        Returns:
            Tuple of (contracts_analyzed, signals_detected)
        """
        # Get quote for underlying price
        quote_data = self.tradier.get_quote([symbol])
        if not quote_data or not isinstance(quote_data, list):
            logger.warning(f"{symbol}: No quote data")
            return 0, 0

        quote = quote_data[0]
        underlying_price = quote.get('last', 0)

        if not underlying_price:
            logger.warning(f"{symbol}: Invalid price")
            return 0, 0

        # Get options chain
        options = self.tradier.get_full_option_chain(symbol, max_expirations=self.config.max_expirations)

        if not options:
            logger.warning(f"{symbol}: No options data")
            return 0, 0

        logger.debug(f"{symbol}: Got {len(options)} contracts at ${underlying_price:.2f}")

        # Calculate current metrics
        current_metrics = self._calculate_metrics(symbol, options, underlying_price)

        # Get historical metrics for averages
        historical = self.db.get_historical_metrics(symbol, days=self.config.historical_lookback_days)

        # Calculate averages and trends
        enhanced_metrics = self._enhance_metrics(current_metrics, historical, quote)

        # Save current metrics
        self.db.save_metrics(symbol, enhanced_metrics, scan_id)

        # Save individual contracts
        for contract in options:
            contract['underlying_price'] = underlying_price
            contract['dte'] = self._calculate_dte(contract.get('expiration_date'))
            self.db.save_option_contract(contract, scan_id)

        # Evaluate filters (gates)
        filters_passed, filter_results = rule_engine.evaluate_filters(enhanced_metrics, options)

        if not filters_passed:
            logger.debug(f"{symbol}: Did not pass filters")
            return len(options), 0

        logger.info(f"{symbol}: PASSED all filters ✓")

        # Evaluate signals
        signal_results = rule_engine.evaluate_signals(enhanced_metrics, options, historical)

        # Evaluate combo signals
        combo_results = rule_engine.evaluate_combos(enhanced_metrics, options, historical)

        # Combine all signals
        all_signals = signal_results + combo_results

        # Save signals to database
        signals_saved = 0
        for signal_result in all_signals:
            signal_data = self._build_signal_data(symbol, signal_result, enhanced_metrics)
            self.db.save_signal(signal_data, scan_id)
            signals_saved += 1

            logger.info(f"  🐋 {signal_result.rule_name}: {signal_result.description} "
                       f"(strength: {signal_result.signal_strength})")

        return len(options), signals_saved

    def _calculate_metrics(self, symbol: str, options: List[Dict], underlying_price: float) -> Dict[str, Any]:
        """Calculate aggregate metrics from options chain"""
        # Use Tradier client's built-in calculator
        metrics = self.tradier.calculate_metrics(options, underlying_price)

        return metrics

    def _enhance_metrics(self, current: Dict[str, Any], historical: List[Dict[str, Any]],
                        quote: Dict) -> Dict[str, Any]:
        """Enhance current metrics with historical averages and trends"""
        enhanced = current.copy()

        if historical:
            # Volume averages
            volumes = [h.get('total_volume', 0) for h in historical if h.get('total_volume')]
            if volumes:
                enhanced['avg_20d_volume'] = int(statistics.mean(volumes))
                if len(volumes) >= 10:
                    enhanced['avg_10d_volume'] = int(statistics.mean(volumes[:10]))

            # P/C averages and stddev
            pc_ratios = [h.get('pc_ratio_volume') for h in historical if h.get('pc_ratio_volume')]
            if pc_ratios:
                enhanced['avg_pc_20d'] = statistics.mean(pc_ratios)
                enhanced['stddev_pc'] = statistics.stdev(pc_ratios) if len(pc_ratios) > 1 else 0.1
                if len(pc_ratios) >= 10:
                    enhanced['avg_pc_10d'] = statistics.mean(pc_ratios[:10])

            # OI changes (compare to previous)
            if len(historical) > 0:
                prev = historical[0]
                enhanced['call_oi_change'] = current.get('total_call_oi', 0) - prev.get('total_call_oi', 0)
                enhanced['put_oi_change'] = current.get('total_put_oi', 0) - prev.get('total_put_oi', 0)

            # IV metrics
            ivs = [h.get('avg_call_iv') for h in historical if h.get('avg_call_iv')]
            if ivs and current.get('avg_call_iv'):
                # Simple IV rank calculation (current position in historical range)
                iv_min = min(ivs)
                iv_max = max(ivs)
                iv_current = current.get('avg_call_iv', 0)
                if iv_max > iv_min:
                    enhanced['iv_rank'] = ((iv_current - iv_min) / (iv_max - iv_min)) * 100
                else:
                    enhanced['iv_rank'] = 50

        # Price trend
        price_change = quote.get('change_percentage', 0)
        enhanced['price_change_pct'] = price_change

        if abs(price_change) < 0.5:
            enhanced['price_trend'] = 'flat'
        elif price_change > 0:
            enhanced['price_trend'] = 'up'
        else:
            enhanced['price_trend'] = 'down'

        return enhanced

    def _calculate_dte(self, expiration: str) -> Optional[int]:
        """Calculate days to expiration"""
        try:
            exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            return (exp_date - date.today()).days
        except:
            return None

    def _build_signal_data(self, symbol: str, result: RuleEvaluationResult,
                          metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build signal data dictionary for database"""
        return {
            'symbol': symbol,
            'signal_type': result.rule_name,
            'signal_strength': result.signal_strength,
            'rule_name': result.rule_name,
            'description': result.description,
            'action_recommended': result.action_recommended,
            'volume': metrics.get('total_volume'),
            'open_interest': metrics.get('total_oi'),
            'oi_change': metrics.get('call_oi_change', 0) + metrics.get('put_oi_change', 0),
            'pc_ratio': metrics.get('pc_ratio_volume'),
            'iv_rank': metrics.get('iv_rank'),
            'volume_avg_ratio': metrics.get('total_volume', 0) / metrics.get('avg_20d_volume', 1) if metrics.get('avg_20d_volume') else None,
            'underlying_price': metrics.get('underlying_price'),
            'price_trend': metrics.get('price_trend'),
            'expires_at': datetime.now() + timedelta(hours=24),
            'metadata': result.metadata
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Whale Options Scanner')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once',
                       help='Run mode: once or continuous')
    parser.add_argument('--interval', type=int, default=60,
                       help='Scan interval in seconds (continuous mode)')
    parser.add_argument('--expirations', type=int, default=5,
                       help='Number of expirations to scan per symbol')

    args = parser.parse_args()

    # Create scanner
    config = ScannerConfig(
        scan_interval=args.interval,
        max_expirations=args.expirations
    )

    scanner = WhaleScanner(config=config)

    # Run
    if args.mode == 'once':
        results = scanner.run_once()
        print(f"\nScan Results:")
        print(f"  Symbols: {results['symbols_scanned']}")
        print(f"  Contracts: {results['contracts_analyzed']:,}")
        print(f"  Signals: {results['signals_detected']}")
        print(f"  Duration: {results['duration_seconds']:.1f}s")

    else:
        scanner.run_continuous()


if __name__ == '__main__':
    main()
