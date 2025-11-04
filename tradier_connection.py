"""
Tradier API Connection Module
Replaces IBKR connection for whale options scanner
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class TradierConnection:
    """Handles connection and data retrieval from Tradier API"""

    def __init__(self, api_token: str, sandbox: bool = True):
        """
        Initialize Tradier connection

        Args:
            api_token: Tradier API access token
            sandbox: Use sandbox environment (default: True)
        """
        self.api_token = api_token
        self.sandbox = sandbox

        # Set base URL based on environment
        self.base_url = "https://sandbox.tradier.com/v1" if sandbox else "https://api.tradier.com/v1"

        # Headers for authentication
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json"
        }

        self.connected = False
        logger.info(f"Tradier connection initialized ({'Sandbox' if sandbox else 'Production'})")

    def connect(self) -> bool:
        """
        Test connection to Tradier API

        Returns:
            bool: True if connection successful
        """
        try:
            # First test with user profile endpoint
            logger.info(f"Testing connection to {self.base_url}/user/profile")
            response = requests.get(
                f"{self.base_url}/user/profile",
                headers=self.headers,
                timeout=10
            )

            logger.info(f"Profile response: {response.status_code}")

            if response.status_code == 200:
                profile_data = response.json()
                account_num = profile_data.get('profile', {}).get('account', {}).get('account_number', 'N/A')
                logger.info(f"✓ Authenticated! Account: {account_num}")
                self.connected = True
                return True
            elif response.status_code == 403:
                logger.error("✗ Authentication failed - check your API token")
                logger.error(f"Response: {response.text}")
                return False
            else:
                logger.error(f"✗ Connection failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"✗ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self):
        """Disconnect from Tradier (no-op for REST API)"""
        self.connected = False
        logger.info("Disconnected from Tradier API")

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """
        Get current stock price

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None
        """
        try:
            response = requests.get(
                f"{self.base_url}/markets/quotes",
                params={"symbols": symbol},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                quote = data.get('quotes', {}).get('quote', {})
                return float(quote.get('last', 0))
            else:
                logger.warning(f"Failed to get price for {symbol}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def get_option_expirations(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            List of expiration dates (YYYY-MM-DD format)
        """
        try:
            response = requests.get(
                f"{self.base_url}/markets/options/expirations",
                params={"symbol": symbol},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                expirations = data.get('expirations', {}).get('date', [])
                logger.debug(f"Found {len(expirations)} expirations for {symbol}")
                return expirations
            else:
                logger.warning(f"Failed to get expirations for {symbol}: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting expirations for {symbol}: {e}")
            return []

    def get_options_chain(
        self,
        symbol: str,
        expiration: str,
        include_greeks: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Get options chain for a specific symbol and expiration

        Args:
            symbol: Stock symbol
            expiration: Expiration date (YYYY-MM-DD)
            include_greeks: Include Greeks data (default: True)

        Returns:
            Dictionary with 'calls' and 'puts' DataFrames
        """
        try:
            params = {
                "symbol": symbol,
                "expiration": expiration
            }

            if include_greeks:
                params["greeks"] = "true"

            response = requests.get(
                f"{self.base_url}/markets/options/chains",
                params=params,
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                logger.warning(f"Failed to get options chain: {response.status_code}")
                return {'calls': pd.DataFrame(), 'puts': pd.DataFrame()}

            data = response.json()
            options = data.get('options', {}).get('option', [])

            if not options:
                logger.warning(f"No options data for {symbol} {expiration}")
                return {'calls': pd.DataFrame(), 'puts': pd.DataFrame()}

            # Convert to DataFrame
            df = pd.DataFrame(options)

            # Separate calls and puts
            calls = df[df['option_type'] == 'call'].copy()
            puts = df[df['option_type'] == 'put'].copy()

            # Standardize column names to match IBKR format
            column_mapping = {
                'strike': 'strike',
                'last': 'lastPrice',
                'bid': 'bid',
                'ask': 'ask',
                'volume': 'volume',
                'open_interest': 'openInterest',
                'option_type': 'right'
            }

            for df_type in [calls, puts]:
                if not df_type.empty:
                    df_type.rename(columns=column_mapping, inplace=True)

                    # Extract IV from greeks if available
                    if 'greeks' in df_type.columns:
                        df_type['impliedVolatility'] = df_type['greeks'].apply(
                            lambda x: x.get('mid_iv', 0) if isinstance(x, dict) else 0
                        )
                        df_type['delta'] = df_type['greeks'].apply(
                            lambda x: x.get('delta', 0) if isinstance(x, dict) else 0
                        )
                    else:
                        df_type['impliedVolatility'] = 0
                        df_type['delta'] = 0

                    # Ensure numeric types
                    numeric_cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume',
                                  'openInterest', 'impliedVolatility', 'delta']
                    for col in numeric_cols:
                        if col in df_type.columns:
                            df_type[col] = pd.to_numeric(df_type[col], errors='coerce').fillna(0)

            logger.info(f"Retrieved {len(calls)} calls, {len(puts)} puts for {symbol} {expiration}")

            return {
                'calls': calls,
                'puts': puts
            }

        except Exception as e:
            logger.error(f"Error getting options chain for {symbol} {expiration}: {e}")
            import traceback
            traceback.print_exc()
            return {'calls': pd.DataFrame(), 'puts': pd.DataFrame()}

    def get_option_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get quotes for specific option symbols

        Args:
            symbols: List of option symbols

        Returns:
            Dictionary of option quotes
        """
        try:
            if not symbols:
                return {}

            # Tradier can handle multiple symbols in one request
            symbols_str = ",".join(symbols)

            response = requests.get(
                f"{self.base_url}/markets/options/quotes",
                params={"symbols": symbols_str},
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                logger.warning(f"Failed to get option quotes: {response.status_code}")
                return {}

            data = response.json()
            quotes = data.get('quotes', {}).get('quote', [])

            if not isinstance(quotes, list):
                quotes = [quotes]

            # Convert to dictionary keyed by symbol
            quote_dict = {}
            for quote in quotes:
                symbol = quote.get('symbol', '')
                if symbol:
                    quote_dict[symbol] = quote

            return quote_dict

        except Exception as e:
            logger.error(f"Error getting option quotes: {e}")
            return {}

    def get_historical_volume(
        self,
        symbol: str,
        expiration: str,
        days: int = 10
    ) -> Dict[str, float]:
        """
        Get historical average volume for options (simulated)

        Note: Tradier doesn't provide historical options data directly.
        This returns current volume as a placeholder.

        Args:
            symbol: Stock symbol
            expiration: Expiration date
            days: Number of days (unused)

        Returns:
            Dictionary with average volumes
        """
        logger.warning("Historical volume not available from Tradier - using current volume")

        chain = self.get_options_chain(symbol, expiration, include_greeks=False)

        avg_volumes = {}

        for option_type, df in [('call', chain['calls']), ('put', chain['puts'])]:
            if not df.empty:
                avg_volume = df['volume'].mean()
                avg_volumes[option_type] = avg_volume
            else:
                avg_volumes[option_type] = 0

        return avg_volumes

    def get_market_status(self) -> Dict[str, any]:
        """
        Get market status (open/closed)

        Returns:
            Dictionary with market status
        """
        try:
            response = requests.get(
                f"{self.base_url}/markets/clock",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                clock = data.get('clock', {})
                return {
                    'state': clock.get('state', 'unknown'),
                    'timestamp': clock.get('timestamp', ''),
                    'next_open': clock.get('next_open', ''),
                    'next_close': clock.get('next_close', '')
                }
            else:
                return {'state': 'unknown'}

        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {'state': 'unknown'}


def test_connection():
    """Test Tradier connection"""
    import os

    api_token = os.getenv('TRADIER_TOKEN', 'YapJSqXqDZ5ui8HtoP7QEyIX7CIk')

    print("\n" + "=" * 60)
    print("Testing Tradier Connection")
    print("=" * 60)

    conn = TradierConnection(api_token, sandbox=True)

    if conn.connect():
        print("\n✓ Connection successful!")

        # Test getting SPY price
        print("\nTesting stock quote...")
        price = conn.get_stock_price("SPY")
        if price:
            print(f"  SPY price: ${price}")

        # Test getting expirations
        print("\nTesting options expirations...")
        expirations = conn.get_option_expirations("SPY")
        if expirations:
            print(f"  Found {len(expirations)} expirations")
            print(f"  Next: {expirations[:3]}")

            # Test getting options chain
            if expirations:
                print(f"\nTesting options chain for {expirations[0]}...")
                chain = conn.get_options_chain("SPY", expirations[0])
                print(f"  Calls: {len(chain['calls'])} contracts")
                print(f"  Puts: {len(chain['puts'])} contracts")

        # Test market status
        print("\nTesting market status...")
        status = conn.get_market_status()
        print(f"  Market state: {status.get('state')}")

        conn.disconnect()
    else:
        print("\n✗ Connection failed!")
        print("\nTroubleshooting:")
        print("  1. Verify your API token is correct")
        print("  2. Check that API access is enabled in your Tradier account")
        print("  3. Confirm your sandbox account is active")
        print("  4. Try generating a new API token")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_connection()
