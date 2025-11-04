"""
Tradier Options Data Fetcher
Replaces IBKR data fetcher with Tradier API
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from tradier_connection import TradierConnection

logger = logging.getLogger(__name__)


class TradierOptionsDataFetcher:
    """Fetches options data from Tradier API"""

    def __init__(self, config: dict, api_token: str, sandbox: bool = True):
        """
        Initialize Tradier options data fetcher

        Args:
            config: Configuration dictionary
            api_token: Tradier API token
            sandbox: Use sandbox environment
        """
        self.config = config
        self.tradier = TradierConnection(api_token, sandbox=sandbox)
        self.cache = {}  # Cache for option chains

        # Connect to Tradier
        if not self.tradier.connect():
            logger.warning("Failed to connect to Tradier API - some features may not work")

    def get_option_chain_data(self, symbol: str, expirations: List[int]) -> pd.DataFrame:
        """
        Get complete option chain data for analysis

        Args:
            symbol: Underlying symbol
            expirations: List of days to expiration to scan

        Returns:
            DataFrame with option chain data
        """
        try:
            logger.info(f"Fetching option chain for {symbol}...")

            # Get current price
            current_price = self.tradier.get_stock_price(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return pd.DataFrame()

            logger.info(f"{symbol} current price: ${current_price:.2f}")

            # Get available expirations
            available_expirations = self.tradier.get_option_expirations(symbol)
            if not available_expirations:
                logger.error(f"Could not get expirations for {symbol}")
                return pd.DataFrame()

            # Filter expirations based on target DTEs
            target_expirations = self._get_target_expirations(
                available_expirations,
                expirations
            )

            logger.info(f"Scanning {len(target_expirations)} expirations for {symbol}")

            # Fetch option data for each expiration
            all_options = []
            for expiration in target_expirations:
                # Get options chain
                chain = self.tradier.get_options_chain(symbol, expiration, include_greeks=True)

                calls = chain['calls']
                puts = chain['puts']

                if calls.empty and puts.empty:
                    logger.warning(f"No options data for {symbol} {expiration}")
                    continue

                # Filter strikes based on price range
                strikes_range = self.config['scanning'].get('strikes_range', 20)

                # Process calls
                if not calls.empty:
                    calls_filtered = self._filter_strikes(calls, current_price, strikes_range)
                    calls_filtered['right'] = 'C'
                    calls_filtered['symbol'] = symbol
                    calls_filtered['expiration'] = expiration.replace('-', '')  # Convert to YYYYMMDD
                    calls_filtered['underlying_price'] = current_price
                    all_options.append(calls_filtered)

                # Process puts
                if not puts.empty:
                    puts_filtered = self._filter_strikes(puts, current_price, strikes_range)
                    puts_filtered['right'] = 'P'
                    puts_filtered['symbol'] = symbol
                    puts_filtered['expiration'] = expiration.replace('-', '')  # Convert to YYYYMMDD
                    puts_filtered['underlying_price'] = current_price
                    all_options.append(puts_filtered)

            # Combine all options
            if all_options:
                df = pd.concat(all_options, ignore_index=True)

                # Standardize columns and add calculated fields
                df = self._standardize_dataframe(df)

                logger.info(f"✓ Fetched {len(df)} option contracts for {symbol}")
                return df
            else:
                logger.warning(f"No option data found for {symbol}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _filter_strikes(self, df: pd.DataFrame, current_price: float, range_pct: int) -> pd.DataFrame:
        """
        Filter strikes within range of current price

        Args:
            df: Options DataFrame
            current_price: Current underlying price
            range_pct: Percentage range above/below current price

        Returns:
            Filtered DataFrame
        """
        lower_bound = current_price * (1 - range_pct / 100)
        upper_bound = current_price * (1 + range_pct / 100)

        filtered = df[
            (df['strike'] >= lower_bound) &
            (df['strike'] <= upper_bound)
        ].copy()

        return filtered

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame columns and add calculated fields

        Args:
            df: Raw options DataFrame

        Returns:
            Standardized DataFrame
        """
        try:
            # Ensure required columns exist with proper names
            if 'lastPrice' in df.columns:
                df['last'] = df['lastPrice']
            if 'openInterest' in df.columns:
                df['open_interest'] = df['openInterest']
            else:
                df['open_interest'] = 0

            # Ensure volume exists
            if 'volume' not in df.columns:
                df['volume'] = 0

            # Calculate days to expiration
            df['dte'] = df['expiration'].apply(self._calculate_dte)

            # Calculate moneyness
            df['moneyness'] = ((df['underlying_price'] - df['strike']) / df['underlying_price']) * 100

            # Ensure IV exists
            if 'impliedVolatility' not in df.columns:
                df['impliedVolatility'] = 0
            else:
                # Convert from decimal to percentage if needed
                df['implied_volatility'] = df['impliedVolatility']

            # Rename for consistency
            df['implied_volatility'] = df.get('impliedVolatility', 0)

            # Fill NaN values
            numeric_cols = ['volume', 'open_interest', 'implied_volatility', 'delta', 'last', 'bid', 'ask']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(0)

            return df

        except Exception as e:
            logger.error(f"Error standardizing dataframe: {e}")
            return df

    def _calculate_dte(self, expiration: str) -> int:
        """
        Calculate days to expiration

        Args:
            expiration: Expiration date (YYYYMMDD or YYYY-MM-DD)

        Returns:
            Days to expiration
        """
        try:
            # Remove dashes if present
            exp_str = expiration.replace('-', '')

            exp_date = datetime.strptime(exp_str, '%Y%m%d')
            today = datetime.now()
            dte = (exp_date - today).days

            return max(0, dte)

        except Exception as e:
            logger.debug(f"Error calculating DTE for {expiration}: {e}")
            return 0

    def _get_target_expirations(self, available_expirations: List[str],
                               target_dtes: List[int]) -> List[str]:
        """
        Get expirations closest to target DTEs

        Args:
            available_expirations: Available expiration dates (YYYY-MM-DD format)
            target_dtes: Target days to expiration

        Returns:
            List of expiration dates
        """
        selected = []
        today = datetime.now()

        for target_dte in target_dtes:
            target_date = today + timedelta(days=target_dte)

            # Find closest expiration
            closest = min(
                available_expirations,
                key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date).days)
            )

            if closest not in selected:
                selected.append(closest)

        return selected

    def calculate_pc_ratio(self, df: pd.DataFrame, by: str = 'volume') -> float:
        """
        Calculate Put/Call ratio

        Args:
            df: DataFrame with option data
            by: Calculate by 'volume' or 'oi' (open interest)

        Returns:
            P/C ratio
        """
        try:
            if df.empty:
                return 0.0

            calls = df[df['right'] == 'C']
            puts = df[df['right'] == 'P']

            if by == 'volume':
                call_vol = calls['volume'].sum()
                put_vol = puts['volume'].sum()
            else:  # open interest
                call_vol = calls['open_interest'].sum()
                put_vol = puts['open_interest'].sum()

            if call_vol == 0:
                return 999.0  # Infinite P/C ratio

            pc_ratio = put_vol / call_vol
            return round(pc_ratio, 3)

        except Exception as e:
            logger.error(f"Error calculating P/C ratio: {e}")
            return 0.0

    def calculate_iv_rank(self, current_iv: float, iv_history: pd.Series) -> float:
        """
        Calculate IV Rank (percentile of current IV in historical range)

        Args:
            current_iv: Current implied volatility
            iv_history: Historical IV series

        Returns:
            IV Rank (0-100)
        """
        try:
            if iv_history.empty or current_iv is None:
                return 50.0

            iv_min = iv_history.min()
            iv_max = iv_history.max()

            if iv_max == iv_min:
                return 50.0

            iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
            return round(iv_rank, 2)

        except Exception as e:
            logger.error(f"Error calculating IV rank: {e}")
            return 50.0

    def calculate_skew(self, df: pd.DataFrame, strike: float) -> float:
        """
        Calculate skew (Put IV - Call IV) at a strike

        Args:
            df: DataFrame with option data
            strike: Strike price to calculate skew at

        Returns:
            Skew percentage
        """
        try:
            strike_data = df[df['strike'] == strike]

            call = strike_data[strike_data['right'] == 'C']
            put = strike_data[strike_data['right'] == 'P']

            if call.empty or put.empty:
                return 0.0

            call_iv = call['implied_volatility'].iloc[0]
            put_iv = put['implied_volatility'].iloc[0]

            if call_iv is None or put_iv is None or call_iv == 0:
                return 0.0

            skew = ((put_iv - call_iv) / call_iv) * 100
            return round(skew, 2)

        except Exception as e:
            logger.debug(f"Error calculating skew: {e}")
            return 0.0

    def get_historical_volume(self, symbol: str, days: int = 20) -> pd.DataFrame:
        """
        Get historical volume data

        Note: Tradier doesn't provide historical options volume easily.
        This is a placeholder that returns empty DataFrame.

        Args:
            symbol: Ticker symbol
            days: Number of days to fetch

        Returns:
            DataFrame with historical volume
        """
        logger.warning("Historical options volume not available from Tradier")
        return pd.DataFrame()

    def calculate_oi_delta(self, symbol: str, strike: float, right: str,
                          expiration: str, current_oi: int) -> int:
        """
        Calculate change in open interest from previous day

        Note: Requires historical OI storage - not implemented yet

        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' or 'P'
            expiration: Expiration date
            current_oi: Current open interest

        Returns:
            OI delta (change from yesterday)
        """
        # TODO: Implement with historical storage
        return 0

    def get_avg_volume(self, df: pd.DataFrame, days: int = 20) -> float:
        """
        Calculate average volume from historical data

        Args:
            df: DataFrame with historical data
            days: Number of days to average

        Returns:
            Average volume
        """
        try:
            if df.empty or 'volume' not in df.columns:
                return 0.0

            return df['volume'].tail(days).mean()

        except Exception as e:
            logger.error(f"Error calculating average volume: {e}")
            return 0.0

    def disconnect(self):
        """Disconnect from Tradier API"""
        if self.tradier:
            self.tradier.disconnect()


def test_fetcher():
    """Test Tradier options data fetcher"""
    import os
    import yaml

    print("\n" + "=" * 60)
    print("Testing Tradier Options Data Fetcher")
    print("=" * 60)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    api_token = os.getenv('TRADIER_TOKEN', 'YapJSqXqDZ5ui8HtoP7QEyIX7CIk')

    fetcher = TradierOptionsDataFetcher(config, api_token, sandbox=True)

    # Test fetching SPY options
    symbol = "SPY"
    expirations = [7, 14, 30]  # Target DTEs

    print(f"\nFetching options chain for {symbol}...")
    df = fetcher.get_option_chain_data(symbol, expirations)

    if not df.empty:
        print(f"\n✓ Successfully fetched {len(df)} contracts")
        print(f"\nSample data:")
        print(df[['symbol', 'expiration', 'strike', 'right', 'volume', 'open_interest', 'dte']].head(10))

        # Test P/C ratio calculation
        pc_ratio = fetcher.calculate_pc_ratio(df, by='volume')
        print(f"\nP/C Ratio (volume): {pc_ratio:.3f}")

        pc_ratio_oi = fetcher.calculate_pc_ratio(df, by='oi')
        print(f"P/C Ratio (OI): {pc_ratio_oi:.3f}")

    else:
        print("\n✗ No data fetched")

    fetcher.disconnect()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_fetcher()
