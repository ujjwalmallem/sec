"""
Example Usage Script
Demonstrates how to use the whale scanner components
"""

import logging
from ibkr_connection import get_ibkr_connection
from options_data import OptionsDataFetcher
from whale_filters import WhaleFilters
import yaml

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_connection():
    """Example 1: Test IBKR connection"""
    print("\n" + "="*80)
    print("Example 1: Testing IBKR Connection")
    print("="*80 + "\n")

    # Get IBKR connection
    ibkr = get_ibkr_connection()

    # Connect
    if ibkr.connect():
        print("✓ Successfully connected to IBKR")

        # Check if market is open
        is_open = ibkr.is_market_open()
        print(f"Market is {'OPEN' if is_open else 'CLOSED'}")

        # Get current price for SPY
        spy_price = ibkr.get_current_price("SPY")
        if spy_price:
            print(f"SPY current price: ${spy_price:.2f}")

        # Disconnect
        ibkr.disconnect()
    else:
        print("✗ Failed to connect to IBKR")
        print("\nMake sure:")
        print("1. TWS or IB Gateway is running")
        print("2. API connections are enabled")
        print("3. Port number is correct (7497 for paper trading)")


def example_2_fetch_options():
    """Example 2: Fetch option chain data"""
    print("\n" + "="*80)
    print("Example 2: Fetching Option Chain")
    print("="*80 + "\n")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Connect
    ibkr = get_ibkr_connection()
    if not ibkr.connect():
        print("✗ Could not connect to IBKR")
        return

    # Create data fetcher
    fetcher = OptionsDataFetcher(config)

    # Fetch options for SPY
    symbol = "SPY"
    expirations = [0, 1, 7]  # 0 DTE, 1 DTE, 1 week

    print(f"Fetching option chain for {symbol}...")
    options_df = fetcher.get_option_chain_data(symbol, expirations)

    if not options_df.empty:
        print(f"\n✓ Retrieved {len(options_df)} option contracts")

        # Show sample data
        print("\nSample contracts:")
        print(options_df[['strike', 'right', 'dte', 'volume', 'open_interest', 'implied_volatility']].head(10))

        # Calculate P/C ratio
        pc_ratio = fetcher.calculate_pc_ratio(options_df, by='volume')
        print(f"\nP/C Ratio (Volume): {pc_ratio:.3f}")

        pc_ratio_oi = fetcher.calculate_pc_ratio(options_df, by='oi')
        print(f"P/C Ratio (OI): {pc_ratio_oi:.3f}")

    else:
        print("✗ No option data retrieved")

    ibkr.disconnect()


def example_3_whale_filters():
    """Example 3: Apply whale filters"""
    print("\n" + "="*80)
    print("Example 3: Applying Whale Filters")
    print("="*80 + "\n")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Connect
    ibkr = get_ibkr_connection()
    if not ibkr.connect():
        print("✗ Could not connect to IBKR")
        return

    # Fetch data
    fetcher = OptionsDataFetcher(config)
    symbol = "SPY"
    expirations = [0, 1, 7]

    print(f"Fetching option data for {symbol}...")
    options_df = fetcher.get_option_chain_data(symbol, expirations)

    if options_df.empty:
        print("✗ No data retrieved")
        ibkr.disconnect()
        return

    print(f"✓ Retrieved {len(options_df)} contracts\n")

    # Apply whale filters
    whale_filters = WhaleFilters(config)

    # Mock historical data (in real usage, this comes from database)
    historical_data = {
        'pc_ratios': [0.9, 0.85, 0.88, 0.92, 0.87],
        'avg_volume_20d': 1000000,
        'iv_history': []
    }

    print("Applying whale filters...")
    filtered_df = whale_filters.apply_all_filters(options_df, historical_data)

    # Show whale signals
    whale_signals = filtered_df[filtered_df['whale_signal'] == True]

    if not whale_signals.empty:
        print(f"\n🐋 Found {len(whale_signals)} WHALE SIGNALS!")
        print("\nTop whale contracts:")
        print(whale_signals[['strike', 'right', 'dte', 'volume', 'open_interest', 'signal_strength']].head(10))
    else:
        print("\n✓ No whale signals detected in this scan")

    # Detect whale combos
    combos = whale_filters.detect_whale_combos(filtered_df, historical_data)
    if combos:
        print(f"\n🎯 Found {len(combos)} WHALE COMBO SIGNALS:")
        for combo in combos:
            print(f"\n  {combo['type']}: {combo['description']}")

    ibkr.disconnect()


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("🐋 IBKR Whale Scanner - Example Usage")
    print("="*80)

    try:
        # Run examples
        example_1_basic_connection()
        # example_2_fetch_options()  # Uncomment to run
        # example_3_whale_filters()  # Uncomment to run

        print("\n" + "="*80)
        print("Examples completed!")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)


if __name__ == "__main__":
    main()
