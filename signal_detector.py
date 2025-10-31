"""
Signal Detector
Detects and generates trading signals from whale activity
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from tabulate import tabulate

logger = logging.getLogger(__name__)


class SignalDetector:
    """Detects and formats whale trading signals"""

    def __init__(self, config: dict):
        """Initialize signal detector"""
        self.config = config
        self.active_signals = []

    def detect_signals(self, df: pd.DataFrame, symbol: str,
                      historical_data: Dict, whale_combos: List[Dict]) -> List[Dict]:
        """
        Detect trading signals from filtered data

        Args:
            df: Filtered DataFrame with whale signals
            symbol: Underlying symbol
            historical_data: Historical metrics
            whale_combos: Detected whale combo signals

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Filter for whale signals
            whales = df[df['whale_signal'] == True]

            if whales.empty and not whale_combos:
                return signals

            logger.info(f"🐋 Whale activity detected for {symbol}!")

            # Process individual whale contracts
            for idx, row in whales.iterrows():
                signal = self._create_signal_from_row(row, symbol, historical_data)
                if signal:
                    signals.append(signal)

            # Add combo signals
            for combo in whale_combos:
                combo['symbol'] = symbol
                combo['timestamp'] = datetime.now().isoformat()
                signals.append(combo)

            # Sort by confidence/signal strength
            signals = sorted(
                signals,
                key=lambda x: x.get('signal_strength', 0),
                reverse=True
            )

            self.active_signals.extend(signals)
            return signals

        except Exception as e:
            logger.error(f"Error detecting signals: {e}")
            return []

    def _create_signal_from_row(self, row: pd.Series, symbol: str,
                                historical_data: Dict) -> Optional[Dict]:
        """
        Create signal from DataFrame row

        Args:
            row: DataFrame row with option data
            symbol: Underlying symbol
            historical_data: Historical metrics

        Returns:
            Signal dictionary
        """
        try:
            # Determine signal type based on P/C and flow
            signal_type = self._determine_signal_type(row, historical_data)

            # Determine action
            action = self._determine_action(row, signal_type)

            signal = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'type': signal_type,
                'action': action,
                'strike': row['strike'],
                'expiration': row['expiration'],
                'dte': row['dte'],
                'right': 'CALL' if row['right'] == 'C' else 'PUT',
                'volume': row['volume'],
                'open_interest': row['open_interest'],
                'implied_volatility': row.get('implied_volatility'),
                'underlying_price': row['underlying_price'],
                'signal_strength': row.get('signal_strength', 0),
                'iv_rank': row.get('iv_rank'),
                'premium': row.get('last'),
                'bid': row.get('bid'),
                'ask': row.get('ask'),
            }

            return signal

        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None

    def _determine_signal_type(self, row: pd.Series, historical_data: Dict) -> str:
        """Determine type of whale signal"""

        # Get historical P/C ratio
        pc_ratios = historical_data.get('pc_ratios', [])
        current_pc = pc_ratios[-1] if pc_ratios else 1.0

        # Check for specific patterns
        if row['right'] == 'C':  # Call activity
            if current_pc < 0.5:
                return "EXTREME_BULLISH"
            elif current_pc < 0.7:
                return "BULLISH"
            else:
                return "CALL_HEDGE"
        else:  # Put activity
            if current_pc > 1.5:
                return "EXTREME_BEARISH"
            elif current_pc > 1.3:
                return "BEARISH"
            else:
                return "PUT_HEDGE"

    def _determine_action(self, row: pd.Series, signal_type: str) -> str:
        """Determine recommended action"""

        actions = {
            'EXTREME_BULLISH': 'BUY CALLS / SELL PUT SPREADS',
            'BULLISH': 'BUY CALLS',
            'CALL_HEDGE': 'MONITOR - Potential Hedge',
            'EXTREME_BEARISH': 'BUY PUTS / SELL CALL SPREADS',
            'BEARISH': 'BUY PUTS',
            'PUT_HEDGE': 'MONITOR - Potential Hedge',
        }

        return actions.get(signal_type, 'MONITOR')

    def format_signals(self, signals: List[Dict]) -> str:
        """
        Format signals for display

        Args:
            signals: List of signal dictionaries

        Returns:
            Formatted string for console output
        """
        if not signals:
            return "No whale signals detected."

        output = "\n" + "="*80 + "\n"
        output += "🐋 WHALE SIGNALS DETECTED\n"
        output += "="*80 + "\n\n"

        # Group by symbol
        symbols = {}
        for signal in signals:
            symbol = signal['symbol']
            if symbol not in symbols:
                symbols[symbol] = []
            symbols[symbol].append(signal)

        # Format each symbol's signals
        for symbol, symbol_signals in symbols.items():
            output += f"\n📊 {symbol}\n"
            output += "-" * 80 + "\n"

            # Check for combo signals
            combos = [s for s in symbol_signals if 'type' in s and s['type'] in
                     ['STRONG_BULL', 'INSTITUTIONAL_HEDGE', 'RETAIL_FOMO']]

            if combos:
                output += "\n🎯 HIGH CONVICTION COMBO SIGNALS:\n"
                for combo in combos:
                    output += f"\n  {combo['type']}: {combo['description']}\n"
                    output += f"  P/C Ratio: {combo.get('pc_ratio', 'N/A')}\n"
                    if 'action' in combo:
                        output += f"  Action: {combo['action']}\n"
                    output += f"  Confidence: {combo.get('confidence', 'N/A')}\n"

            # Individual contract signals
            contract_signals = [s for s in symbol_signals if 'strike' in s]

            if contract_signals:
                output += "\n📋 INDIVIDUAL WHALE CONTRACTS:\n\n"

                table_data = []
                for signal in contract_signals[:10]:  # Top 10
                    table_data.append([
                        signal['right'],
                        f"${signal['strike']:.2f}",
                        signal['dte'],
                        f"{signal['volume']:,}",
                        f"{signal['open_interest']:,}",
                        f"{signal.get('implied_volatility', 0):.2%}" if signal.get('implied_volatility') else 'N/A',
                        signal['type'],
                        signal['signal_strength']
                    ])

                headers = ['Type', 'Strike', 'DTE', 'Volume', 'OI', 'IV', 'Signal', 'Strength']
                output += tabulate(table_data, headers=headers, tablefmt='grid')
                output += "\n"

        output += "\n" + "="*80 + "\n"

        return output

    def print_summary(self, all_signals: Dict[str, List[Dict]]):
        """
        Print summary of all signals

        Args:
            all_signals: Dictionary of symbol -> signals
        """
        print("\n" + "="*80)
        print("📊 WHALE SCANNER SUMMARY")
        print("="*80)

        total_signals = sum(len(signals) for signals in all_signals.values())
        print(f"\nTotal Symbols Scanned: {len(all_signals)}")
        print(f"Total Whale Signals: {total_signals}")

        if total_signals > 0:
            print("\n🐋 Whale Activity by Symbol:")
            for symbol, signals in all_signals.items():
                if signals:
                    print(f"  {symbol}: {len(signals)} signals")

            # Print detailed signals
            for symbol, signals in all_signals.items():
                if signals:
                    print(self.format_signals(signals))
        else:
            print("\n✓ No whale signals detected in this scan.")

        print("="*80 + "\n")

    def generate_alert(self, signal: Dict) -> str:
        """
        Generate alert message for a signal

        Args:
            signal: Signal dictionary

        Returns:
            Alert message string
        """
        try:
            if 'strike' in signal:
                # Contract signal
                alert = (
                    f"🐋 WHALE ALERT: {signal['symbol']}\n"
                    f"Type: {signal['type']}\n"
                    f"Contract: {signal['strike']} {signal['right']} ({signal['dte']} DTE)\n"
                    f"Volume: {signal['volume']:,} | OI: {signal['open_interest']:,}\n"
                    f"Action: {signal['action']}\n"
                    f"Signal Strength: {signal['signal_strength']}/100"
                )
            else:
                # Combo signal
                alert = (
                    f"🎯 WHALE COMBO: {signal['symbol']}\n"
                    f"Pattern: {signal['type']}\n"
                    f"Description: {signal['description']}\n"
                    f"Confidence: {signal.get('confidence', 'N/A')}"
                )
                if 'action' in signal:
                    alert += f"\nAction: {signal['action']}"

            return alert

        except Exception as e:
            logger.error(f"Error generating alert: {e}")
            return "Error generating alert"

    def send_alerts(self, signals: List[Dict]):
        """
        Send alerts via configured channels

        Args:
            signals: List of signals to alert on
        """
        alerts_config = self.config.get('alerts', {})

        for signal in signals:
            alert_msg = self.generate_alert(signal)

            # Console alert
            if alerts_config.get('enable_console', True):
                print(f"\n{alert_msg}\n")

            # File logging
            if alerts_config.get('enable_file_logging', False):
                logger.info(alert_msg)

            # Telegram (if configured)
            if alerts_config.get('telegram', {}).get('enabled', False):
                self._send_telegram_alert(alert_msg, alerts_config['telegram'])

            # Email (if configured)
            if alerts_config.get('email', {}).get('enabled', False):
                self._send_email_alert(alert_msg, alerts_config['email'])

    def _send_telegram_alert(self, message: str, config: Dict):
        """Send alert via Telegram"""
        try:
            # Implementation with python-telegram-bot
            # Requires bot_token and chat_id in config
            logger.info("Telegram alert sent (implementation pending)")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")

    def _send_email_alert(self, message: str, config: Dict):
        """Send alert via email"""
        try:
            # Implementation with smtplib
            logger.info("Email alert sent (implementation pending)")
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
