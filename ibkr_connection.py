"""
IBKR Connection Handler
Manages connection to Interactive Brokers TWS/Gateway
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime
from ib_insync import IB, Stock, Option, Contract, util
import yaml

# Enable nested event loops for threading compatibility
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # nest_asyncio is optional but recommended

logger = logging.getLogger(__name__)


class IBKRConnection:
    """Handles IBKR API connection and basic operations"""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize IBKR connection"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.ib = IB()
        self.connected = False
        self.host = self.config['ibkr']['tws']['host']
        self.port = self.config['ibkr']['tws']['port']
        self.client_id = self.config['ibkr']['tws']['client_id']
        self.readonly = self.config['ibkr']['tws']['readonly']

    def connect(self) -> bool:
        """
        Connect to IBKR TWS/Gateway

        Returns:
            bool: True if connection successful
        """
        try:
            if not self.ib.isConnected():
                logger.info(f"Connecting to IBKR at {self.host}:{self.port}")

                # ib_insync requires an event loop - use util.run() for thread safety
                util.run(
                    self.ib.connectAsync(
                        host=self.host,
                        port=self.port,
                        clientId=self.client_id,
                        readonly=self.readonly,
                        timeout=20
                    )
                )

                # Switch to delayed market data (free) if not subscribed to real-time
                # Market data type: 1=delayed, 2=frozen, 3=delayed frozen, 4=real-time
                self.ib.reqMarketDataType(3)  # Use delayed frozen data (free)
                logger.info("✓ Using delayed/snapshot market data (free)")

                self.connected = True
                logger.info("✓ Connected to IBKR successfully")
                return True
            else:
                logger.info("Already connected to IBKR")
                self.connected = True
                return True

        except Exception as e:
            logger.error(f"✗ Failed to connect to IBKR: {e}")
            logger.error("Make sure TWS/Gateway is running and API connections are enabled")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib.isConnected():
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")

    def get_contract(self, symbol: str, sec_type: str = "STK",
                    exchange: str = "SMART", currency: str = "USD") -> Optional[Contract]:
        """
        Get contract details for a symbol

        Args:
            symbol: Ticker symbol
            sec_type: Security type (STK, OPT, FUT, etc.)
            exchange: Exchange
            currency: Currency

        Returns:
            Contract object or None
        """
        try:
            if sec_type == "STK":
                contract = Stock(symbol, exchange, currency)
            else:
                # For other types, need more params
                contract = Contract(
                    symbol=symbol,
                    secType=sec_type,
                    exchange=exchange,
                    currency=currency
                )

            # Qualify contract
            qualified = self.ib.qualifyContracts(contract)
            if qualified:
                return qualified[0]
            else:
                logger.warning(f"Could not qualify contract for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Error getting contract for {symbol}: {e}")
            return None

    def get_option_chain(self, symbol: str, exchange: str = "SMART") -> Optional[List]:
        """
        Get option chain for a symbol

        Args:
            symbol: Underlying symbol
            exchange: Exchange

        Returns:
            List of option chain details
        """
        try:
            # Get underlying contract
            contract = self.get_contract(symbol)
            if not contract:
                return None

            # Request option chain
            logger.info(f"Fetching option chain for {symbol}...")
            chains = self.ib.reqSecDefOptParams(
                underlyingSymbol=symbol,
                futFopExchange="",
                underlyingSecType="STK",
                underlyingConId=contract.conId
            )

            if not chains:
                logger.warning(f"No option chains found for {symbol}")
                return None

            logger.info(f"✓ Found {len(chains)} option chain(s) for {symbol}")
            return chains

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return None

    def get_option_contracts(self, symbol: str, expiration: str,
                            strike: float, right: str = "C") -> Optional[Contract]:
        """
        Get specific option contract

        Args:
            symbol: Underlying symbol
            expiration: Expiration date (YYYYMMDD)
            strike: Strike price
            right: Option right ('C' for call, 'P' for put)

        Returns:
            Option contract
        """
        try:
            # Use CBOE exchange instead of SMART to avoid ARCA subscription errors
            # CBOE supports delayed data without additional subscriptions
            option = Option(
                symbol=symbol,
                lastTradeDateOrContractMonth=expiration,
                strike=strike,
                right=right,
                exchange="CBOE"  # Changed from SMART to CBOE
            )

            qualified = self.ib.qualifyContracts(option)
            if qualified:
                return qualified[0]
            return None

        except Exception as e:
            logger.error(f"Error getting option contract: {e}")
            return None

    def get_market_data(self, contract: Contract, snapshot: bool = False):
        """
        Get market data for a contract

        Args:
            contract: Contract to get data for
            snapshot: If True, return snapshot data

        Returns:
            Market data
        """
        try:
            if snapshot:
                # Request snapshot
                ticker = self.ib.reqMktData(contract, snapshot=True)
                # Wait for data
                self.ib.sleep(2)
                return ticker
            else:
                # Request streaming data
                ticker = self.ib.reqMktData(contract)
                return ticker

        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None

    def get_option_greeks(self, contract: Contract):
        """
        Get option Greeks

        Args:
            contract: Option contract

        Returns:
            Greeks data
        """
        try:
            ticker = self.ib.reqMktData(contract, genericTickList='106')
            self.ib.sleep(2)
            return ticker

        except Exception as e:
            logger.error(f"Error getting Greeks: {e}")
            return None

    def get_historical_data(self, contract: Contract, duration: str = "30 D",
                           bar_size: str = "1 day", what_to_show: str = "TRADES"):
        """
        Get historical data

        Args:
            contract: Contract
            duration: Duration string (e.g., "30 D", "1 M")
            bar_size: Bar size (e.g., "1 day", "1 hour")
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK)

        Returns:
            Historical data bars
        """
        try:
            bars = self.ib.reqHistoricalData(
                contract=contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=True,
                formatDate=1
            )
            return bars

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol

        Args:
            symbol: Ticker symbol

        Returns:
            Current price or None
        """
        try:
            contract = self.get_contract(symbol)
            if not contract:
                return None

            ticker = self.get_market_data(contract, snapshot=True)
            if ticker and ticker.marketPrice():
                return ticker.marketPrice()

            # Fallback to last price
            if ticker and ticker.last:
                return ticker.last

            return None

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    def is_market_open(self) -> bool:
        """
        Check if market is open

        Returns:
            True if market is open
        """
        try:
            # US market hours: 9:30 AM - 4:00 PM ET
            now = datetime.now()
            weekday = now.weekday()

            # Check if weekend
            if weekday >= 5:  # Saturday = 5, Sunday = 6
                return False

            # Check time (simplified - doesn't account for holidays)
            hour = now.hour
            if 9 <= hour < 16:
                if hour == 9 and now.minute < 30:
                    return False
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return False

    def keep_alive(self):
        """Keep connection alive by requesting time"""
        try:
            if self.ib.isConnected():
                self.ib.reqCurrentTime()
        except Exception as e:
            logger.warning(f"Keep-alive failed: {e}")


# Singleton instance
_ibkr_connection = None


def get_ibkr_connection(config_path: str = "config.yaml") -> IBKRConnection:
    """Get or create IBKR connection singleton"""
    global _ibkr_connection
    if _ibkr_connection is None:
        _ibkr_connection = IBKRConnection(config_path)
    return _ibkr_connection
