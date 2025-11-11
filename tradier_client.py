"""
Tradier API Client
Clean, simple client for fetching options data from Tradier API
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class TradierConfig:
    """Tradier API configuration"""
    api_key: str
    account_id: str
    sandbox: bool = True

    @property
    def base_url(self) -> str:
        if self.sandbox:
            return "https://sandbox.tradier.com/v1"
        return "https://api.tradier.com/v1"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }


class TradierClient:
    """
    Tradier API Client for options data

    Features:
    - Get options chains with Greeks
    - Real-time quotes
    - Historical data
    - Market calendar
    - Rate limiting and error handling
    """

    def __init__(self, config: Optional[TradierConfig] = None):
        """
        Initialize Tradier client

        Args:
            config: TradierConfig object, or None to load from environment
        """
        if config is None:
            api_key = os.getenv('TRADIER_API_KEY', '')
            account_id = os.getenv('TRADIER_ACCOUNT_ID', '')
            sandbox = os.getenv('TRADIER_SANDBOX', 'true').lower() == 'true'

            if not api_key or not account_id:
                raise ValueError("TRADIER_API_KEY and TRADIER_ACCOUNT_ID must be set")

            config = TradierConfig(
                api_key=api_key,
                account_id=account_id,
                sandbox=sandbox
            )

        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 10 requests/second max

        logger.info(f"Tradier client initialized ({'sandbox' if config.sandbox else 'production'} mode)")

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request to Tradier API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response JSON
        """
        self._rate_limit()

        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def get_quote(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get real-time quotes for symbols

        Args:
            symbols: List of ticker symbols

        Returns:
            Quote data dictionary
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        params = {'symbols': ','.join(symbols)}
        data = self._request('GET', 'markets/quotes', params=params)

        return data.get('quotes', {}).get('quote', [])

    def get_option_expirations(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates for a symbol

        Args:
            symbol: Ticker symbol

        Returns:
            List of expiration dates (YYYY-MM-DD format)
        """
        params = {'symbol': symbol}
        data = self._request('GET', 'markets/options/expirations', params=params)

        expirations = data.get('expirations', {}).get('date', [])

        if isinstance(expirations, str):
            expirations = [expirations]

        return expirations

    def get_option_chain(self, symbol: str, expiration: str, greeks: bool = True) -> List[Dict]:
        """
        Get option chain for a symbol and expiration

        Args:
            symbol: Ticker symbol
            expiration: Expiration date (YYYY-MM-DD)
            greeks: Include Greeks calculations

        Returns:
            List of option contracts with details
        """
        params = {
            'symbol': symbol,
            'expiration': expiration,
            'greeks': str(greeks).lower()
        }

        data = self._request('GET', 'markets/options/chains', params=params)

        options = data.get('options', {}).get('option', [])

        if isinstance(options, dict):
            options = [options]

        return options if options else []

    def get_full_option_chain(self, symbol: str, max_expirations: int = 5) -> List[Dict]:
        """
        Get full option chain across multiple expirations

        Args:
            symbol: Ticker symbol
            max_expirations: Maximum number of expirations to fetch

        Returns:
            List of all option contracts
        """
        # Get expirations
        expirations = self.get_option_expirations(symbol)

        if not expirations:
            logger.warning(f"No expirations found for {symbol}")
            return []

        # Limit expirations
        expirations = expirations[:max_expirations]
        logger.info(f"Fetching {len(expirations)} expirations for {symbol}")

        all_options = []
        for exp_date in expirations:
            try:
                chain = self.get_option_chain(symbol, exp_date, greeks=True)
                all_options.extend(chain)
                logger.debug(f"{symbol} {exp_date}: {len(chain)} contracts")
            except Exception as e:
                logger.error(f"Error fetching chain for {symbol} {exp_date}: {e}")
                continue

        return all_options

    def get_historical_data(self, symbol: str, interval: str = 'daily',
                           start: Optional[date] = None, end: Optional[date] = None) -> List[Dict]:
        """
        Get historical price data

        Args:
            symbol: Ticker symbol
            interval: 'daily', 'weekly', 'monthly'
            start: Start date
            end: End date

        Returns:
            List of historical price bars
        """
        params = {
            'symbol': symbol,
            'interval': interval
        }

        if start:
            params['start'] = start.isoformat()
        if end:
            params['end'] = end.isoformat()

        data = self._request('GET', 'markets/history', params=params)

        history = data.get('history', {}).get('day', [])

        if isinstance(history, dict):
            history = [history]

        return history

    def get_market_calendar(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """
        Get market calendar (trading days, holidays)

        Args:
            month: Month (1-12)
            year: Year

        Returns:
            Calendar data
        """
        params = {}
        if month:
            params['month'] = month
        if year:
            params['year'] = year

        data = self._request('GET', 'markets/calendar', params=params)
        return data.get('calendar', {})

    def is_market_open(self) -> bool:
        """
        Check if market is currently open

        Returns:
            True if market is open, False otherwise
        """
        data = self._request('GET', 'markets/clock')
        clock = data.get('clock', {})
        return clock.get('state', '') == 'open'

    def calculate_metrics(self, options: List[Dict], underlying_price: float) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from options chain

        Args:
            options: List of option contracts
            underlying_price: Current underlying price

        Returns:
            Dictionary of calculated metrics
        """
        if not options:
            return {}

        calls = [opt for opt in options if opt.get('option_type') == 'call']
        puts = [opt for opt in options if opt.get('option_type') == 'put']

        # Volume metrics
        call_volume = sum(opt.get('volume', 0) or 0 for opt in calls)
        put_volume = sum(opt.get('volume', 0) or 0 for opt in puts)
        total_volume = call_volume + put_volume

        # OI metrics
        call_oi = sum(opt.get('open_interest', 0) or 0 for opt in calls)
        put_oi = sum(opt.get('open_interest', 0) or 0 for opt in puts)
        total_oi = call_oi + put_oi

        # P/C ratios
        pc_ratio_volume = put_volume / call_volume if call_volume > 0 else None
        pc_ratio_oi = put_oi / call_oi if call_oi > 0 else None

        # IV metrics
        call_ivs = [opt.get('greeks', {}).get('mid_iv', 0) or 0 for opt in calls if opt.get('greeks')]
        put_ivs = [opt.get('greeks', {}).get('mid_iv', 0) or 0 for opt in puts if opt.get('greeks')]

        avg_call_iv = sum(call_ivs) / len(call_ivs) if call_ivs else None
        avg_put_iv = sum(put_ivs) / len(put_ivs) if put_ivs else None

        put_call_iv_skew = None
        if avg_put_iv and avg_call_iv:
            put_call_iv_skew = (avg_put_iv - avg_call_iv) / avg_call_iv

        return {
            'total_call_volume': call_volume,
            'total_put_volume': put_volume,
            'total_volume': total_volume,
            'total_call_oi': call_oi,
            'total_put_oi': put_oi,
            'total_oi': total_oi,
            'pc_ratio_volume': pc_ratio_volume,
            'pc_ratio_oi': pc_ratio_oi,
            'avg_call_iv': avg_call_iv,
            'avg_put_iv': avg_put_iv,
            'put_call_iv_skew': put_call_iv_skew,
            'underlying_price': underlying_price,
            'contracts_analyzed': len(options)
        }

    def __repr__(self) -> str:
        mode = 'sandbox' if self.config.sandbox else 'production'
        return f"TradierClient(mode={mode}, account={self.config.account_id})"


if __name__ == '__main__':
    # Test the client
    logging.basicConfig(level=logging.INFO)

    client = TradierClient()
    print(client)

    # Test market status
    is_open = client.is_market_open()
    print(f"\nMarket is: {'OPEN' if is_open else 'CLOSED'}")

    # Test quote
    quote = client.get_quote(['SPY'])
    print(f"\nSPY Quote: ${quote[0].get('last', 'N/A')}")

    # Test expirations
    expirations = client.get_option_expirations('SPY')
    print(f"\nNext 5 SPY expirations: {expirations[:5]}")

    # Test option chain (first expiration)
    if expirations:
        chain = client.get_option_chain('SPY', expirations[0])
        print(f"\nSPY {expirations[0]} chain: {len(chain)} contracts")

        # Calculate metrics
        if quote:
            spy_price = quote[0].get('last', 0)
            metrics = client.calculate_metrics(chain, spy_price)
            print(f"\nMetrics:")
            print(f"  Total Volume: {metrics.get('total_volume'):,}")
            print(f"  Total OI: {metrics.get('total_oi'):,}")
            print(f"  P/C Ratio (Volume): {metrics.get('pc_ratio_volume', 0):.2f}")
            print(f"  P/C Ratio (OI): {metrics.get('pc_ratio_oi', 0):.2f}")
