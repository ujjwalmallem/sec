"""
Options Data Fetcher
Fetches and processes options data from IBKR
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ib_insync import Option, util
from ibkr_connection import get_ibkr_connection

logger = logging.getLogger(__name__)


class OptionsDataFetcher:
    """Fetches options data and calculates metrics"""

    def __init__(self, config: dict):
        """Initialize options data fetcher"""
        self.config = config
        self.ibkr = get_ibkr_connection()
        self.cache = {}  # Cache for option chains

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
            current_price = self.ibkr.get_current_price(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return pd.DataFrame()

            logger.info(f"{symbol} current price: ${current_price:.2f}")

            # Get option chain
            chains = self.ibkr.get_option_chain(symbol)
            if not chains:
                return pd.DataFrame()

            # Process each chain
            all_options = []
            for chain in chains:
                logger.info(f"Processing chain: {chain.exchange}")

                # Filter expirations based on config
                target_dates = self._get_target_expirations(
                    chain.expirations,
                    expirations
                )

                # Get strikes around current price
                strikes = self._get_relevant_strikes(
                    chain.strikes,
                    current_price,
                    self.config['scanning']['strikes_range']
                )

                # Fetch option data for each expiration and strike
                for expiration in target_dates:
                    for strike in strikes:
                        # Get call
                        call_data = self._get_option_data(
                            symbol, expiration, strike, 'C', current_price
                        )
                        if call_data:
                            all_options.append(call_data)

                        # Get put
                        put_data = self._get_option_data(
                            symbol, expiration, strike, 'P', current_price
                        )
                        if put_data:
                            all_options.append(put_data)

            # Convert to DataFrame
            if all_options:
                df = pd.DataFrame(all_options)
                logger.info(f"✓ Fetched {len(df)} option contracts for {symbol}")
                return df
            else:
                logger.warning(f"No option data found for {symbol}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return pd.DataFrame()

    def _get_option_data(self, symbol: str, expiration: str, strike: float,
                        right: str, underlying_price: float) -> Optional[Dict]:
        """
        Get data for a single option contract

        Args:
            symbol: Underlying symbol
            expiration: Expiration date
            strike: Strike price
            right: 'C' or 'P'
            underlying_price: Current underlying price

        Returns:
            Dictionary with option data
        """
        try:
            # Get contract
            contract = self.ibkr.get_option_contracts(symbol, expiration, strike, right)
            if not contract:
                return None

            # Get market data
            ticker = self.ibkr.get_market_data(contract, snapshot=True)
            if not ticker:
                return None

            # Wait for data to populate
            self.ibkr.ib.sleep(0.5)

            # Extract data
            data = {
                'symbol': symbol,
                'expiration': expiration,
                'strike': strike,
                'right': right,
                'underlying_price': underlying_price,
                'last': ticker.last if ticker.last == ticker.last else None,  # NaN check
                'bid': ticker.bid if ticker.bid == ticker.bid else None,
                'ask': ticker.ask if ticker.ask == ticker.ask else None,
                'volume': ticker.volume if ticker.volume == ticker.volume else 0,
                'open_interest': ticker.openInterest if hasattr(ticker, 'openInterest') else 0,
                'implied_volatility': ticker.impliedVolatility if hasattr(ticker, 'impliedVolatility') else None,
                'delta': ticker.modelGreeks.delta if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else None,
                'gamma': ticker.modelGreeks.gamma if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else None,
                'theta': ticker.modelGreeks.theta if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else None,
                'vega': ticker.modelGreeks.vega if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks else None,
            }

            # Calculate days to expiration
            exp_date = datetime.strptime(expiration, '%Y%m%d')
            today = datetime.now()
            data['dte'] = (exp_date - today).days

            # Calculate moneyness
            data['moneyness'] = (underlying_price - strike) / underlying_price * 100

            return data

        except Exception as e:
            logger.debug(f"Error getting option data for {symbol} {expiration} {strike}{right}: {e}")
            return None

    def _get_target_expirations(self, available_expirations: List[str],
                               target_dtes: List[int]) -> List[str]:
        """
        Get expirations closest to target DTEs

        Args:
            available_expirations: Available expiration dates
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
                key=lambda x: abs((datetime.strptime(x, '%Y%m%d') - target_date).days)
            )

            if closest not in selected:
                selected.append(closest)

        return selected

    def _get_relevant_strikes(self, available_strikes: List[float],
                            current_price: float, range_pct: int = 20) -> List[float]:
        """
        Get strikes within range of current price

        Args:
            available_strikes: Available strikes
            current_price: Current underlying price
            range_pct: Percentage range above/below current price

        Returns:
            List of strikes
        """
        lower_bound = current_price * (1 - range_pct / 100)
        upper_bound = current_price * (1 + range_pct / 100)

        relevant = [
            strike for strike in available_strikes
            if lower_bound <= strike <= upper_bound
        ]

        return sorted(relevant)

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

        Args:
            symbol: Ticker symbol
            days: Number of days to fetch

        Returns:
            DataFrame with historical volume
        """
        try:
            contract = self.ibkr.get_contract(symbol)
            if not contract:
                return pd.DataFrame()

            bars = self.ibkr.get_historical_data(
                contract=contract,
                duration=f"{days} D",
                bar_size="1 day",
                what_to_show="TRADES"
            )

            if not bars:
                return pd.DataFrame()

            # Convert to DataFrame
            df = util.df(bars)
            return df

        except Exception as e:
            logger.error(f"Error getting historical volume: {e}")
            return pd.DataFrame()

    def calculate_oi_delta(self, symbol: str, strike: float, right: str,
                          expiration: str, current_oi: int) -> int:
        """
        Calculate change in open interest from previous day

        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' or 'P'
            expiration: Expiration date
            current_oi: Current open interest

        Returns:
            OI delta (change from yesterday)
        """
        # This would require storing historical OI data
        # For now, return 0 or implement with database
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
