"""
Whale Filters
Implements all whale detection filters and conditions
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class WhaleFilters:
    """Implements whale detection filters"""

    def __init__(self, config: dict):
        """Initialize whale filters with configuration"""
        self.config = config
        self.liquidity_gate = config['whale_filters']['liquidity_gate']
        self.anomaly_gate = config['whale_filters']['anomaly_gate']
        self.conviction_gate = config['whale_filters']['conviction_gate']
        self.volatility_gate = config['whale_filters']['volatility_gate']
        self.custom_scanner = config['custom_scanner']

    def apply_all_filters(self, df: pd.DataFrame, historical_data: Dict) -> pd.DataFrame:
        """
        Apply all whale filters in sequence

        Args:
            df: DataFrame with option data
            historical_data: Dictionary with historical metrics

        Returns:
            Filtered DataFrame with whale signals
        """
        logger.info("Applying whale filters...")

        if df.empty:
            return df

        # Make a copy
        result = df.copy()

        # Add filter flags
        result['passed_liquidity_gate'] = False
        result['passed_anomaly_gate'] = False
        result['passed_conviction_gate'] = False
        result['passed_volatility_gate'] = False
        result['whale_signal'] = False
        result['signal_strength'] = 0

        # Apply filters in order
        result = self.filter_liquidity_gate(result)
        result = self.filter_anomaly_gate(result, historical_data)
        result = self.filter_conviction_gate(result, historical_data)
        result = self.filter_volatility_gate(result, historical_data)

        # Determine whale signals (all gates passed)
        result['whale_signal'] = (
            result['passed_liquidity_gate'] &
            result['passed_anomaly_gate'] &
            result['passed_conviction_gate'] &
            result['passed_volatility_gate']
        )

        # Calculate signal strength (0-100)
        result['signal_strength'] = (
            result['passed_liquidity_gate'].astype(int) * 25 +
            result['passed_anomaly_gate'].astype(int) * 25 +
            result['passed_conviction_gate'].astype(int) * 25 +
            result['passed_volatility_gate'].astype(int) * 25
        )

        whale_count = result['whale_signal'].sum()
        logger.info(f"✓ Found {whale_count} whale signals")

        return result

    def filter_liquidity_gate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter 1: Liquidity Gate
        Volume > 500K AND OI > 100K per expiry

        Args:
            df: Option data DataFrame

        Returns:
            DataFrame with liquidity_gate flag
        """
        try:
            # Group by expiration to check total volume/OI per expiry
            for expiration in df['expiration'].unique():
                exp_data = df[df['expiration'] == expiration]

                total_volume = exp_data['volume'].sum()
                total_oi = exp_data['open_interest'].sum()

                # Check if expiry meets liquidity requirements
                if (total_volume >= self.liquidity_gate['min_volume'] and
                    total_oi >= self.liquidity_gate['min_oi']):

                    # Mark individual contracts that meet strike OI requirement
                    df.loc[
                        (df['expiration'] == expiration) &
                        (df['open_interest'] >= self.liquidity_gate['min_oi_per_strike']),
                        'passed_liquidity_gate'
                    ] = True

            passed = df['passed_liquidity_gate'].sum()
            logger.info(f"Liquidity Gate: {passed} contracts passed")

            return df

        except Exception as e:
            logger.error(f"Error in liquidity gate: {e}")
            return df

    def filter_anomaly_gate(self, df: pd.DataFrame, historical_data: Dict) -> pd.DataFrame:
        """
        Filter 2: Anomaly Gate
        P/C ratio deviates >1.5σ from 20-day average

        Args:
            df: Option data DataFrame
            historical_data: Historical P/C ratios

        Returns:
            DataFrame with anomaly_gate flag
        """
        try:
            # Calculate current P/C ratio
            calls = df[df['right'] == 'C']
            puts = df[df['right'] == 'P']

            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()

            if call_volume == 0:
                return df

            current_pc_ratio = put_volume / call_volume

            # Get historical P/C ratios
            if 'pc_ratios' not in historical_data or len(historical_data['pc_ratios']) < 2:
                # Not enough historical data, use threshold-based approach
                if current_pc_ratio <= self.anomaly_gate['pc_whale_threshold']:
                    df['passed_anomaly_gate'] = True
                    logger.info(f"Anomaly Gate: P/C={current_pc_ratio:.3f} (Whale threshold)")
            else:
                pc_history = pd.Series(historical_data['pc_ratios'])
                pc_mean = pc_history.mean()
                pc_std = pc_history.std()

                # Check if current P/C deviates by threshold * std
                deviation = abs(current_pc_ratio - pc_mean) / pc_std if pc_std > 0 else 0

                if deviation >= self.anomaly_gate['pc_deviation_threshold']:
                    df['passed_anomaly_gate'] = True
                    logger.info(
                        f"Anomaly Gate: P/C={current_pc_ratio:.3f}, "
                        f"Mean={pc_mean:.3f}, Deviation={deviation:.2f}σ"
                    )

            # Also flag extreme P/C ratios
            if (current_pc_ratio < self.anomaly_gate['pc_bullish_threshold'] or
                current_pc_ratio > self.anomaly_gate['pc_bearish_threshold']):
                df['passed_anomaly_gate'] = True

            passed = df['passed_anomaly_gate'].sum()
            logger.info(f"Anomaly Gate: {passed} contracts passed")

            return df

        except Exception as e:
            logger.error(f"Error in anomaly gate: {e}")
            return df

    def filter_conviction_gate(self, df: pd.DataFrame, historical_data: Dict) -> pd.DataFrame:
        """
        Filter 3: Conviction Gate
        Volume > 2x avg AND OI increasing in flow direction

        Args:
            df: Option data DataFrame
            historical_data: Historical volume data

        Returns:
            DataFrame with conviction_gate flag
        """
        try:
            # Get average volume from historical data
            avg_volume = historical_data.get('avg_volume_20d', 0)

            if avg_volume == 0:
                # Fallback to using current data
                avg_volume = df['volume'].mean()

            # Check volume multiplier
            for idx, row in df.iterrows():
                current_vol = row['volume']

                # Volume > 2x average
                if current_vol >= avg_volume * self.conviction_gate['volume_vs_avg_multiplier']:

                    # Check OI growth (simplified - would need historical OI data)
                    # For now, use OI > threshold as proxy
                    if row['open_interest'] >= self.conviction_gate['oi_delta_threshold']:
                        df.at[idx, 'passed_conviction_gate'] = True

            passed = df['passed_conviction_gate'].sum()
            logger.info(f"Conviction Gate: {passed} contracts passed (avg_vol={avg_volume:.0f})")

            return df

        except Exception as e:
            logger.error(f"Error in conviction gate: {e}")
            return df

    def filter_volatility_gate(self, df: pd.DataFrame, historical_data: Dict) -> pd.DataFrame:
        """
        Filter 4: Volatility Gate
        IVR in top/bottom 10% of 1-year range

        Args:
            df: Option data DataFrame
            historical_data: Historical IV data

        Returns:
            DataFrame with volatility_gate flag
        """
        try:
            # For each option, check if IV rank is extreme
            for idx, row in df.iterrows():
                current_iv = row.get('implied_volatility')

                if current_iv is None or pd.isna(current_iv):
                    continue

                # Get IV history for this symbol (simplified)
                iv_history = historical_data.get('iv_history', [])

                if not iv_history:
                    # Use threshold approach
                    # Mark as passed if IV is available (will refine with data)
                    continue

                # Calculate IV Rank
                iv_series = pd.Series(iv_history)
                iv_min = iv_series.min()
                iv_max = iv_series.max()

                if iv_max == iv_min:
                    continue

                iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100

                # Check if in extreme range
                if (iv_rank >= self.volatility_gate['ivr_expensive'] or
                    iv_rank <= self.volatility_gate['ivr_cheap']):
                    df.at[idx, 'passed_volatility_gate'] = True
                    df.at[idx, 'iv_rank'] = iv_rank

            passed = df['passed_volatility_gate'].sum()
            logger.info(f"Volatility Gate: {passed} contracts passed")

            return df

        except Exception as e:
            logger.error(f"Error in volatility gate: {e}")
            return df

    def detect_whale_combos(self, df: pd.DataFrame, historical_data: Dict) -> List[Dict]:
        """
        Detect whale combo signals (high conviction patterns)

        Args:
            df: Option data DataFrame
            historical_data: Historical metrics

        Returns:
            List of detected combo signals
        """
        signals = []

        try:
            # Calculate current metrics
            calls = df[df['right'] == 'C']
            puts = df[df['right'] == 'P']

            call_volume = calls['volume'].sum()
            put_volume = puts['volume'].sum()
            call_oi = calls['open_interest'].sum()
            put_oi = puts['open_interest'].sum()

            pc_ratio = put_volume / call_volume if call_volume > 0 else 0
            avg_volume = historical_data.get('avg_volume_20d', 1)

            # Get IV rank (simplified)
            avg_iv = df['implied_volatility'].mean()

            # 1. Strong Bull Signal
            strong_bull = self.config['whale_combos']['strong_bull']
            if (pc_ratio <= strong_bull['pc_ratio_max'] and
                call_volume >= avg_volume * strong_bull['call_volume_min_multiplier']):

                signals.append({
                    'type': 'STRONG_BULL',
                    'description': 'Low P/C + High Call Volume + Rising Call OI',
                    'pc_ratio': pc_ratio,
                    'call_volume': call_volume,
                    'call_oi': call_oi,
                    'confidence': 'HIGH'
                })

            # 2. Institutional Crash Protection
            inst_crash = self.config['whale_combos']['institutional_crash_protection']
            if (pc_ratio >= inst_crash['pc_ratio_min'] and
                put_volume >= avg_volume * inst_crash['put_volume_spike_multiplier']):

                signals.append({
                    'type': 'INSTITUTIONAL_HEDGE',
                    'description': 'High P/C + Put Volume Spike + Rising Put OI',
                    'pc_ratio': pc_ratio,
                    'put_volume': put_volume,
                    'put_oi': put_oi,
                    'confidence': 'HIGH'
                })

            # 3. Retail FOMO (Fade Signal)
            retail_fomo = self.config['whale_combos']['retail_fomo']
            if (pc_ratio <= retail_fomo['pc_ratio_max'] and
                call_volume >= avg_volume * retail_fomo['volume_multiplier']):

                # Check if OI is NOT increasing significantly (retail day trading)
                if call_oi < retail_fomo['oi_change_max']:
                    signals.append({
                        'type': 'RETAIL_FOMO',
                        'description': 'Extreme Low P/C + High Volume + No OI Change',
                        'pc_ratio': pc_ratio,
                        'volume': call_volume,
                        'oi': call_oi,
                        'action': 'FADE (Sell Iron Condors)',
                        'confidence': 'MEDIUM'
                    })

            return signals

        except Exception as e:
            logger.error(f"Error detecting whale combos: {e}")
            return []

    def check_volume_oi_divergence(self, row: pd.Series) -> str:
        """
        Check for volume/OI divergence patterns

        Args:
            row: DataFrame row with option data

        Returns:
            Pattern description
        """
        try:
            volume = row['volume']
            oi = row['open_interest']

            # High volume, low OI = noise/day trading
            if volume > oi * 2 and oi < 1000:
                return "HIGH_VOL_LOW_OI (Noise - Avoid)"

            # Low volume, high OI = trapped positions
            if oi > 10000 and volume < oi * 0.1:
                return "LOW_VOL_HIGH_OI (Breakout Setup)"

            # High volume, high OI = conviction
            if volume > 1000 and oi > 5000:
                return "HIGH_VOL_HIGH_OI (Conviction Trade)"

            return "NORMAL"

        except Exception as e:
            return "ERROR"

    def calculate_signal_score(self, row: pd.Series, historical_data: Dict) -> float:
        """
        Calculate overall signal score (0-100)

        Args:
            row: DataFrame row with option data
            historical_data: Historical metrics

        Returns:
            Signal score
        """
        score = 0.0

        try:
            # Volume score (0-25)
            avg_volume = historical_data.get('avg_volume_20d', 1)
            volume_ratio = row['volume'] / avg_volume if avg_volume > 0 else 0
            volume_score = min(25, (volume_ratio / 5) * 25)  # Cap at 5x = 25 points
            score += volume_score

            # OI score (0-25)
            if row['open_interest'] >= 100000:
                oi_score = 25
            elif row['open_interest'] >= 50000:
                oi_score = 20
            elif row['open_interest'] >= 10000:
                oi_score = 15
            elif row['open_interest'] >= 5000:
                oi_score = 10
            else:
                oi_score = 0
            score += oi_score

            # P/C score (0-25) - extreme values get higher scores
            # This would need symbol-level P/C, simplified here
            score += 12.5  # Placeholder

            # IV score (0-25)
            if 'iv_rank' in row and not pd.isna(row['iv_rank']):
                if row['iv_rank'] >= 90 or row['iv_rank'] <= 10:
                    iv_score = 25
                elif row['iv_rank'] >= 80 or row['iv_rank'] <= 20:
                    iv_score = 20
                else:
                    iv_score = 10
            else:
                iv_score = 0
            score += iv_score

            return round(score, 2)

        except Exception as e:
            logger.error(f"Error calculating signal score: {e}")
            return 0.0
