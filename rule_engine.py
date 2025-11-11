"""
Whale Rule Engine
Evaluates configurable whale detection rules against market data
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation"""
    passed: bool
    rule_name: str
    rule_type: str
    signal_strength: int  # 0-100
    description: str
    action_recommended: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WhaleRuleEngine:
    """
    Evaluates whale detection rules against market data

    Implements all whale trading logic:
    - Four-gate filtering (Liquidity, Anomaly, Conviction, Volatility)
    - Signal detection (Strong Bull, Institutional Hedge, etc.)
    - Combo signals (Whale Conviction, Custom Scanner)
    - OI pattern rules
    - IV rules
    """

    def __init__(self, rules: List[Dict[str, Any]]):
        """
        Initialize rule engine

        Args:
            rules: List of whale rules from database
        """
        self.rules = rules

        # Organize rules by type
        self.filters = [r for r in rules if r['rule_type'] == 'FILTER']
        self.signals = [r for r in rules if r['rule_type'] == 'SIGNAL']
        self.combos = [r for r in rules if r['rule_type'] == 'COMBO']

        logger.info(f"Rule engine initialized: {len(self.filters)} filters, "
                   f"{len(self.signals)} signals, {len(self.combos)} combos")

    def evaluate_filters(self, metrics: Dict[str, Any],
                        options: List[Dict[str, Any]]) -> Tuple[bool, List[RuleEvaluationResult]]:
        """
        Evaluate all filter rules (gates)

        Args:
            metrics: Aggregated metrics for symbol
            options: List of option contracts

        Returns:
            Tuple of (all_passed, results_list)
        """
        results = []

        for rule in self.filters:
            result = self._evaluate_filter(rule, metrics, options)
            results.append(result)

            # If any filter fails, return early
            if not result.passed:
                logger.debug(f"Filter failed: {rule['rule_name']}")
                return False, results

        return True, results

    def evaluate_signals(self, metrics: Dict[str, Any],
                        options: List[Dict[str, Any]],
                        historical: List[Dict[str, Any]]) -> List[RuleEvaluationResult]:
        """
        Evaluate signal detection rules

        Args:
            metrics: Current aggregated metrics
            options: List of option contracts
            historical: Historical metrics for trend analysis

        Returns:
            List of detected signals
        """
        signals = []

        for rule in self.signals:
            result = self._evaluate_signal(rule, metrics, options, historical)
            if result.passed:
                signals.append(result)
                logger.info(f"Signal detected: {rule['rule_name']} "
                          f"(strength: {result.signal_strength})")

        return signals

    def evaluate_combos(self, metrics: Dict[str, Any],
                       options: List[Dict[str, Any]],
                       historical: List[Dict[str, Any]]) -> List[RuleEvaluationResult]:
        """
        Evaluate combo signal rules (high conviction patterns)

        Args:
            metrics: Current aggregated metrics
            options: List of option contracts
            historical: Historical metrics

        Returns:
            List of detected combo signals
        """
        combos = []

        for rule in self.combos:
            result = self._evaluate_combo(rule, metrics, options, historical)
            if result.passed:
                combos.append(result)
                logger.info(f"Combo signal detected: {rule['rule_name']} "
                          f"(strength: {result.signal_strength})")

        return combos

    # ========================================================================
    # FILTER EVALUATION
    # ========================================================================

    def _evaluate_filter(self, rule: Dict[str, Any], metrics: Dict[str, Any],
                        options: List[Dict[str, Any]]) -> RuleEvaluationResult:
        """Evaluate a single filter rule"""
        rule_name = rule['rule_name']
        config = rule['rule_config']

        # Liquidity Gate
        if rule_name == 'liquidity_gate':
            return self._check_liquidity_gate(config, metrics, options)

        # Anomaly Gate
        elif rule_name == 'anomaly_gate':
            return self._check_anomaly_gate(config, metrics)

        # Conviction Gate
        elif rule_name == 'conviction_gate':
            return self._check_conviction_gate(config, metrics)

        # Volatility Gate
        elif rule_name == 'volatility_gate':
            return self._check_volatility_gate(config, metrics)

        # Basic filters
        elif rule_name == 'volume_greater_than_oi':
            passed = metrics.get('total_volume', 0) > metrics.get('total_oi', 0)
            return RuleEvaluationResult(
                passed=passed,
                rule_name=rule_name,
                rule_type='FILTER',
                signal_strength=100 if passed else 0,
                description="Volume exceeds OI" if passed else "Volume <= OI"
            )

        elif rule_name == 'min_oi_threshold':
            min_oi = config.get('min_oi', 5000)
            total_oi = metrics.get('total_oi', 0)
            passed = total_oi >= min_oi
            return RuleEvaluationResult(
                passed=passed,
                rule_name=rule_name,
                rule_type='FILTER',
                signal_strength=100 if passed else 0,
                description=f"OI {total_oi:,} {'≥' if passed else '<'} {min_oi:,}"
            )

        elif rule_name == 'pc_ratio_extreme':
            max_pc = config.get('max_pc_ratio', 0.3)
            pc_ratio = metrics.get('pc_ratio_volume', 999)
            passed = pc_ratio is not None and pc_ratio <= max_pc
            return RuleEvaluationResult(
                passed=passed,
                rule_name=rule_name,
                rule_type='FILTER',
                signal_strength=100 if passed else 0,
                description=f"P/C {pc_ratio:.2f if pc_ratio != 999 else 'N/A'} "
                           f"{'≤' if passed else '>'} {max_pc}"
            )

        else:
            # Unknown filter - pass by default
            return RuleEvaluationResult(
                passed=True,
                rule_name=rule_name,
                rule_type='FILTER',
                signal_strength=50,
                description="Unknown filter (skipped)"
            )

    def _check_liquidity_gate(self, config: Dict, metrics: Dict,
                             options: List[Dict]) -> RuleEvaluationResult:
        """Gate 1: Liquidity filter"""
        min_volume = config.get('min_volume', 500000)
        min_oi = config.get('min_oi', 100000)

        total_volume = metrics.get('total_volume', 0)
        total_oi = metrics.get('total_oi', 0)

        passed = total_volume >= min_volume and total_oi >= min_oi

        return RuleEvaluationResult(
            passed=passed,
            rule_name='liquidity_gate',
            rule_type='FILTER',
            signal_strength=100 if passed else 0,
            description=f"Liquidity: Vol {total_volume:,}/{min_volume:,}, OI {total_oi:,}/{min_oi:,}"
        )

    def _check_anomaly_gate(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """Gate 2: P/C ratio anomaly"""
        threshold = config.get('pc_deviation_threshold', 1.5)

        pc_ratio = metrics.get('pc_ratio_volume')
        avg_pc = metrics.get('avg_pc_20d')
        stddev_pc = metrics.get('stddev_pc')

        if pc_ratio is None or avg_pc is None or stddev_pc is None:
            return RuleEvaluationResult(
                passed=False,
                rule_name='anomaly_gate',
                rule_type='FILTER',
                signal_strength=0,
                description="Insufficient historical data for P/C anomaly"
            )

        deviation = abs(pc_ratio - avg_pc) / stddev_pc if stddev_pc > 0 else 0
        passed = deviation > threshold

        return RuleEvaluationResult(
            passed=passed,
            rule_name='anomaly_gate',
            rule_type='FILTER',
            signal_strength=min(int(deviation * 50), 100) if passed else 0,
            description=f"P/C anomaly: {deviation:.1f}σ deviation (threshold: {threshold}σ)"
        )

    def _check_conviction_gate(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """Gate 3: Volume vs OI conviction"""
        vol_multiplier = config.get('volume_vs_avg_multiplier', 2.0)
        oi_delta_min = config.get('oi_delta_min', 25000)

        total_volume = metrics.get('total_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        oi_change = abs(metrics.get('call_oi_change', 0)) + abs(metrics.get('put_oi_change', 0))

        volume_ratio = total_volume / avg_volume if avg_volume > 0 else 0
        passed = volume_ratio >= vol_multiplier and oi_change >= oi_delta_min

        return RuleEvaluationResult(
            passed=passed,
            rule_name='conviction_gate',
            rule_type='FILTER',
            signal_strength=min(int(volume_ratio * 30), 100) if passed else 0,
            description=f"Conviction: Vol {volume_ratio:.1f}x avg, OI Δ {oi_change:,}"
        )

    def _check_volatility_gate(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """Gate 4: IV Rank extremes"""
        ivr_high = config.get('ivr_expensive', 80)
        ivr_low = config.get('ivr_cheap', 20)

        iv_rank = metrics.get('iv_rank')

        if iv_rank is None:
            return RuleEvaluationResult(
                passed=False,
                rule_name='volatility_gate',
                rule_type='FILTER',
                signal_strength=0,
                description="No IV Rank data"
            )

        passed = iv_rank >= ivr_high or iv_rank <= ivr_low

        return RuleEvaluationResult(
            passed=passed,
            rule_name='volatility_gate',
            rule_type='FILTER',
            signal_strength=100 if passed else 0,
            description=f"IV Rank: {iv_rank:.0f} ({'expensive' if iv_rank >= ivr_high else 'cheap' if iv_rank <= ivr_low else 'neutral'})"
        )

    # ========================================================================
    # SIGNAL EVALUATION
    # ========================================================================

    def _evaluate_signal(self, rule: Dict, metrics: Dict, options: List[Dict],
                        historical: List[Dict]) -> RuleEvaluationResult:
        """Evaluate a single signal rule"""
        rule_name = rule['rule_name']
        config = rule['rule_config']

        # Strong Bull Signal
        if rule_name == 'strong_bull_signal':
            return self._check_strong_bull(config, metrics, historical)

        # Institutional Hedge
        elif rule_name == 'institutional_hedge':
            return self._check_institutional_hedge(config, metrics, historical)

        # Retail FOMO
        elif rule_name == 'retail_fomo':
            return self._check_retail_fomo(config, metrics, historical)

        # OI Patterns
        elif rule_name == 'smart_money_long':
            return self._check_smart_money_long(config, metrics)

        elif rule_name == 'hedging_pattern':
            return self._check_hedging_pattern(config, metrics)

        elif rule_name == 'short_squeeze_fuel':
            return self._check_short_squeeze(config, metrics)

        # IV Rules
        elif rule_name == 'iv_crush_opportunity':
            return self._check_iv_crush(config, metrics)

        elif rule_name == 'cheap_volatility':
            return self._check_cheap_vol(config, metrics)

        else:
            return RuleEvaluationResult(
                passed=False,
                rule_name=rule_name,
                rule_type='SIGNAL',
                signal_strength=0,
                description="Unknown signal rule"
            )

    def _check_strong_bull(self, config: Dict, metrics: Dict,
                          historical: List[Dict]) -> RuleEvaluationResult:
        """Strong bullish: Low P/C + High call vol + Rising call OI + Low IVR"""
        pc_max = config.get('pc_ratio_max', 0.7)
        call_vol_mult = config.get('call_volume_min_multiplier', 2.0)
        ivr_max = config.get('ivr_max', 30)

        pc_ratio = metrics.get('pc_ratio_volume', 999)
        call_oi_change = metrics.get('call_oi_change', 0)
        iv_rank = metrics.get('iv_rank', 100)

        # Calculate call volume ratio
        call_volume = metrics.get('total_call_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        call_vol_ratio = call_volume / (avg_volume * 0.6) if avg_volume > 0 else 0  # Assume 60% calls typically

        passed = (
            pc_ratio <= pc_max and
            call_vol_ratio >= call_vol_mult and
            call_oi_change > 0 and
            iv_rank <= ivr_max
        )

        strength = 0
        if passed:
            strength = min(int((1 - pc_ratio) * 100 + call_vol_ratio * 20), 100)

        return RuleEvaluationResult(
            passed=passed,
            rule_name='strong_bull_signal',
            rule_type='SIGNAL',
            signal_strength=strength,
            description=f"Strong Bull: P/C {pc_ratio:.2f}, Call Vol {call_vol_ratio:.1f}x, "
                       f"Call OI {'↑' if call_oi_change > 0 else '↓'}, IVR {iv_rank:.0f}",
            action_recommended='FOLLOW' if passed else None
        )

    def _check_institutional_hedge(self, config: Dict, metrics: Dict,
                                  historical: List[Dict]) -> RuleEvaluationResult:
        """Crash protection: High P/C + Put spike + Rising put OI + High IVR"""
        pc_min = config.get('pc_ratio_min', 1.3)
        put_vol_mult = config.get('put_volume_spike_multiplier', 3.0)
        ivr_min = config.get('ivr_min', 90)

        pc_ratio = metrics.get('pc_ratio_volume', 0)
        put_oi_change = metrics.get('put_oi_change', 0)
        iv_rank = metrics.get('iv_rank', 0)

        put_volume = metrics.get('total_put_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        put_vol_ratio = put_volume / (avg_volume * 0.4) if avg_volume > 0 else 0  # Assume 40% puts typically

        passed = (
            pc_ratio >= pc_min and
            put_vol_ratio >= put_vol_mult and
            put_oi_change > 0 and
            iv_rank >= ivr_min
        )

        strength = 0
        if passed:
            strength = min(int(pc_ratio * 50 + put_vol_ratio * 15), 100)

        return RuleEvaluationResult(
            passed=passed,
            rule_name='institutional_hedge',
            rule_type='SIGNAL',
            signal_strength=strength,
            description=f"Institutional Hedge: P/C {pc_ratio:.2f}, Put Vol {put_vol_ratio:.1f}x, "
                       f"Put OI {'↑' if put_oi_change > 0 else '↓'}, IVR {iv_rank:.0f}",
            action_recommended='BUY_DIPS' if passed else None
        )

    def _check_retail_fomo(self, config: Dict, metrics: Dict,
                          historical: List[Dict]) -> RuleEvaluationResult:
        """Retail FOMO: P/C <0.3 + Volume 5x avg + No OI change (FADE)"""
        pc_max = config.get('pc_ratio_max', 0.3)
        vol_mult = config.get('volume_multiplier', 5.0)
        oi_change_max = config.get('oi_change_max', 1000)

        pc_ratio = metrics.get('pc_ratio_volume', 999)
        total_volume = metrics.get('total_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        total_oi_change = abs(metrics.get('call_oi_change', 0)) + abs(metrics.get('put_oi_change', 0))

        vol_ratio = total_volume / avg_volume if avg_volume > 0 else 0

        passed = (
            pc_ratio <= pc_max and
            vol_ratio >= vol_mult and
            total_oi_change < oi_change_max
        )

        return RuleEvaluationResult(
            passed=passed,
            rule_name='retail_fomo',
            rule_type='SIGNAL',
            signal_strength=min(int(vol_ratio * 15), 100) if passed else 0,
            description=f"Retail FOMO: P/C {pc_ratio:.2f}, Vol {vol_ratio:.1f}x, OI Δ {total_oi_change:,}",
            action_recommended='FADE' if passed else None
        )

    def _check_smart_money_long(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """OI ↑ in Calls + Price ↑ = Smart money long"""
        call_oi_change = metrics.get('call_oi_change', 0)
        price_trend = metrics.get('price_trend', 'flat')

        passed = call_oi_change > 10000 and price_trend == 'up'

        return RuleEvaluationResult(
            passed=passed,
            rule_name='smart_money_long',
            rule_type='SIGNAL',
            signal_strength=min(int(call_oi_change / 500), 100) if passed else 0,
            description=f"Smart Money Long: Call OI +{call_oi_change:,}, Price {price_trend}",
            action_recommended='FOLLOW' if passed else None
        )

    def _check_hedging_pattern(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """OI ↑ in Puts + Price ↑ = Hedging (not bearish)"""
        put_oi_change = metrics.get('put_oi_change', 0)
        price_trend = metrics.get('price_trend', 'flat')

        passed = put_oi_change > 10000 and price_trend == 'up'

        return RuleEvaluationResult(
            passed=passed,
            rule_name='hedging_pattern',
            rule_type='SIGNAL',
            signal_strength=min(int(put_oi_change / 500), 100) if passed else 0,
            description=f"Hedging Pattern: Put OI +{put_oi_change:,}, Price {price_trend}",
            action_recommended='IGNORE' if passed else None
        )

    def _check_short_squeeze(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """OI ↓ in Puts + Price ↓ = Put covering, short squeeze fuel"""
        put_oi_change = metrics.get('put_oi_change', 0)
        price_trend = metrics.get('price_trend', 'flat')

        passed = put_oi_change < -10000 and price_trend == 'down'

        return RuleEvaluationResult(
            passed=passed,
            rule_name='short_squeeze_fuel',
            rule_type='SIGNAL',
            signal_strength=min(int(abs(put_oi_change) / 500), 100) if passed else 0,
            description=f"Short Squeeze Fuel: Put OI {put_oi_change:,}, Price {price_trend}",
            action_recommended='BUY_CALLS' if passed else None
        )

    def _check_iv_crush(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """Sell premium when IVR >90 pre-event"""
        ivr_min = config.get('ivr_min', 90)
        iv_rank = metrics.get('iv_rank', 0)

        passed = iv_rank >= ivr_min

        return RuleEvaluationResult(
            passed=passed,
            rule_name='iv_crush_opportunity',
            rule_type='SIGNAL',
            signal_strength=int(iv_rank) if passed else 0,
            description=f"IV Crush Opportunity: IVR {iv_rank:.0f}",
            action_recommended='SELL_PREMIUM' if passed else None
        )

    def _check_cheap_vol(self, config: Dict, metrics: Dict) -> RuleEvaluationResult:
        """Buy calendars when IVR <10"""
        ivr_max = config.get('ivr_max', 10)
        iv_rank = metrics.get('iv_rank', 100)

        passed = iv_rank <= ivr_max

        return RuleEvaluationResult(
            passed=passed,
            rule_name='cheap_volatility',
            rule_type='SIGNAL',
            signal_strength=int(100 - iv_rank) if passed else 0,
            description=f"Cheap Volatility: IVR {iv_rank:.0f}",
            action_recommended='BUY_CALENDARS' if passed else None
        )

    # ========================================================================
    # COMBO EVALUATION
    # ========================================================================

    def _evaluate_combo(self, rule: Dict, metrics: Dict, options: List[Dict],
                       historical: List[Dict]) -> RuleEvaluationResult:
        """Evaluate combo signal rule"""
        rule_name = rule['rule_name']
        config = rule['rule_config']

        if rule_name == 'whale_conviction':
            return self._check_whale_conviction(config, metrics, historical)

        elif rule_name == 'custom_scanner':
            return self._check_custom_scanner(config, metrics, historical)

        else:
            return RuleEvaluationResult(
                passed=False,
                rule_name=rule_name,
                rule_type='COMBO',
                signal_strength=0,
                description="Unknown combo rule"
            )

    def _check_whale_conviction(self, config: Dict, metrics: Dict,
                               historical: List[Dict]) -> RuleEvaluationResult:
        """High conviction whale: Volume >2x + P/C deviation + OI delta + IV extreme"""
        vol_mult = config.get('volume_multiplier', 2.0)
        pc_dev_sigma = config.get('pc_deviation_sigma', 1.5)
        oi_delta_min = config.get('oi_delta_min', 10000)

        # Volume check
        total_volume = metrics.get('total_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        vol_ratio = total_volume / avg_volume if avg_volume > 0 else 0

        # P/C deviation
        pc_ratio = metrics.get('pc_ratio_volume')
        avg_pc = metrics.get('avg_pc_20d')
        stddev_pc = metrics.get('stddev_pc', 1)
        pc_deviation = abs(pc_ratio - avg_pc) / stddev_pc if pc_ratio and avg_pc and stddev_pc > 0 else 0

        # OI change
        total_oi_change = abs(metrics.get('call_oi_change', 0)) + abs(metrics.get('put_oi_change', 0))

        # IV extreme
        iv_rank = metrics.get('iv_rank', 50)
        iv_extreme = iv_rank > 80 or iv_rank < 20

        passed = (
            vol_ratio >= vol_mult and
            pc_deviation >= pc_dev_sigma and
            total_oi_change >= oi_delta_min and
            iv_extreme
        )

        strength = 0
        if passed:
            strength = min(int(vol_ratio * 20 + pc_deviation * 20 + total_oi_change / 500), 100)

        return RuleEvaluationResult(
            passed=passed,
            rule_name='whale_conviction',
            rule_type='COMBO',
            signal_strength=strength,
            description=f"Whale Conviction: Vol {vol_ratio:.1f}x, P/C dev {pc_deviation:.1f}σ, "
                       f"OI Δ {total_oi_change:,}, IVR {iv_rank:.0f}",
            action_recommended='STRONG_FOLLOW' if passed else None
        )

    def _check_custom_scanner(self, config: Dict, metrics: Dict,
                             historical: List[Dict]) -> RuleEvaluationResult:
        """Custom scanner: Volume spike + P/C anomaly + OI change + IV extremes"""
        vol_vs_20d = config.get('volume_vs_20d_avg', 2.0)
        pc_dev_sigma = config.get('pc_deviation_sigma', 1.5)
        oi_change_min = config.get('oi_change_min', 10000)
        ivr_high = config.get('ivr_high', 80)
        ivr_low = config.get('ivr_low', 20)

        # Checks
        total_volume = metrics.get('total_volume', 0)
        avg_volume = metrics.get('avg_20d_volume', 1)
        vol_ratio = total_volume / avg_volume if avg_volume > 0 else 0

        pc_ratio = metrics.get('pc_ratio_volume')
        avg_pc = metrics.get('avg_pc_20d')
        stddev_pc = metrics.get('stddev_pc', 1)
        pc_deviation = abs(pc_ratio - avg_pc) / stddev_pc if pc_ratio and avg_pc and stddev_pc > 0 else 0

        total_oi_change = abs(metrics.get('call_oi_change', 0)) + abs(metrics.get('put_oi_change', 0))

        iv_rank = metrics.get('iv_rank', 50)
        iv_extreme = iv_rank >= ivr_high or iv_rank <= ivr_low

        passed = (
            vol_ratio >= vol_vs_20d and
            pc_deviation >= pc_dev_sigma and
            total_oi_change >= oi_change_min and
            iv_extreme
        )

        strength = min(int(vol_ratio * 25 + pc_deviation * 25), 100) if passed else 0

        return RuleEvaluationResult(
            passed=passed,
            rule_name='custom_scanner',
            rule_type='COMBO',
            signal_strength=strength,
            description=f"Custom Scanner: Vol {vol_ratio:.1f}x, P/C dev {pc_deviation:.1f}σ, "
                       f"OI Δ {total_oi_change:,}, IVR {iv_rank:.0f}",
            action_recommended='ALERT' if passed else None
        )


if __name__ == '__main__':
    # Test rule engine
    logging.basicConfig(level=logging.INFO)

    # Mock rules
    test_rules = [
        {
            'rule_name': 'liquidity_gate',
            'rule_type': 'FILTER',
            'rule_config': {'min_volume': 500000, 'min_oi': 100000}
        },
        {
            'rule_name': 'strong_bull_signal',
            'rule_type': 'SIGNAL',
            'rule_config': {'pc_ratio_max': 0.7, 'call_volume_min_multiplier': 2.0, 'ivr_max': 30}
        }
    ]

    # Mock data
    test_metrics = {
        'total_volume': 1000000,
        'total_oi': 200000,
        'pc_ratio_volume': 0.5,
        'avg_pc_20d': 0.9,
        'stddev_pc': 0.2,
        'iv_rank': 25,
        'call_oi_change': 15000,
        'total_call_volume': 700000,
        'avg_20d_volume': 300000
    }

    engine = WhaleRuleEngine(test_rules)

    # Test filter
    all_passed, filter_results = engine.evaluate_filters(test_metrics, [])
    print(f"\nFilters passed: {all_passed}")
    for result in filter_results:
        print(f"  {result.rule_name}: {result.description}")

    # Test signal
    signal_results = engine.evaluate_signals(test_metrics, [], [])
    print(f"\nSignals detected: {len(signal_results)}")
    for result in signal_results:
        print(f"  {result.rule_name}: {result.description} (strength: {result.signal_strength})")
