"""
Flask Web Application for Whale Scanner
Provides web-based UI for monitoring whale options activity
"""

import logging
import json
import threading
import time
from datetime import datetime
from typing import Dict, List

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import yaml

from ibkr_connection import get_ibkr_connection
from options_data import OptionsDataFetcher
from whale_filters import WhaleFilters
from signal_detector import SignalDetector
from data_storage import DataStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'whale-scanner-secret-key-change-me'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global state
scanner_state = {
    'running': False,
    'connected': False,
    'current_signals': [],
    'scan_count': 0,
    'last_scan': None,
    'config': None,
    'watchlist': [],
    'recent_scans': []
}

scanner_thread = None
scanner_lock = threading.Lock()


def load_config():
    """Load configuration"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        scanner_state['config'] = config
        scanner_state['watchlist'] = config['watchlist']['symbols']
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None


def init_scanner_components(config):
    """Initialize scanner components"""
    try:
        ibkr = get_ibkr_connection()
        data_fetcher = OptionsDataFetcher(config)
        whale_filters = WhaleFilters(config)
        signal_detector = SignalDetector(config)
        data_storage = DataStorage(config)

        return {
            'ibkr': ibkr,
            'data_fetcher': data_fetcher,
            'whale_filters': whale_filters,
            'signal_detector': signal_detector,
            'data_storage': data_storage
        }
    except Exception as e:
        logger.error(f"Error initializing scanner: {e}")
        return None


def scan_symbol(symbol: str, components: Dict) -> Dict:
    """Scan a single symbol"""
    try:
        logger.info(f"Scanning {symbol}...")

        # Fetch option chain data
        expirations = scanner_state['config']['scanning']['expirations_to_scan']
        options_df = components['data_fetcher'].get_option_chain_data(symbol, expirations)

        if options_df.empty:
            return {'symbol': symbol, 'signals': [], 'error': 'No data'}

        # Get historical data
        historical_data = components['data_storage'].get_historical_metrics(symbol)

        # Calculate current metrics
        current_metrics = calculate_metrics(options_df, symbol, components)

        # Store current data
        components['data_storage'].store_metrics(symbol, current_metrics)

        # Apply whale filters
        filtered_df = components['whale_filters'].apply_all_filters(options_df, historical_data)

        # Detect whale combo signals
        whale_combos = components['whale_filters'].detect_whale_combos(filtered_df, historical_data)

        # Detect trading signals
        signals = components['signal_detector'].detect_signals(
            filtered_df,
            symbol,
            historical_data,
            whale_combos
        )

        result = {
            'symbol': symbol,
            'signals': [serialize_signal(s) for s in signals],
            'metrics': current_metrics,
            'timestamp': datetime.now().isoformat(),
            'contracts_scanned': len(options_df),
            'whale_signals': len([s for s in signals if 'signal_strength' in s and s['signal_strength'] > 75])
        }

        return result

    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
        return {'symbol': symbol, 'signals': [], 'error': str(e)}


def calculate_metrics(df, symbol, components):
    """Calculate current metrics for a symbol"""
    try:
        pc_ratio = components['data_fetcher'].calculate_pc_ratio(df, by='volume')
        pc_ratio_oi = components['data_fetcher'].calculate_pc_ratio(df, by='oi')

        calls = df[df['right'] == 'C']
        puts = df[df['right'] == 'P']

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'underlying_price': float(df['underlying_price'].iloc[0]) if not df.empty else 0,
            'pc_ratio_volume': float(pc_ratio),
            'pc_ratio_oi': float(pc_ratio_oi),
            'total_volume': int(df['volume'].sum()),
            'total_oi': int(df['open_interest'].sum()),
            'call_volume': int(calls['volume'].sum()),
            'put_volume': int(puts['volume'].sum()),
            'call_oi': int(calls['open_interest'].sum()),
            'put_oi': int(puts['open_interest'].sum()),
            'avg_iv': float(df['implied_volatility'].mean()) if 'implied_volatility' in df.columns else 0,
        }
        return metrics
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {}


def serialize_signal(signal: Dict) -> Dict:
    """Convert signal to JSON-serializable format"""
    serialized = {}
    for key, value in signal.items():
        if isinstance(value, (int, float, str, bool, type(None))):
            serialized[key] = value
        else:
            serialized[key] = str(value)
    return serialized


def scanner_worker():
    """Background scanner worker"""
    logger.info("Scanner worker started")

    # Load config
    config = load_config()
    if not config:
        logger.error("Failed to load config")
        return

    # Initialize components
    components = init_scanner_components(config)
    if not components:
        logger.error("Failed to initialize scanner")
        return

    # Connect to IBKR
    if not components['ibkr'].connect():
        logger.error("Failed to connect to IBKR")
        scanner_state['connected'] = False
        socketio.emit('scanner_error', {'message': 'Failed to connect to IBKR'})
        return

    scanner_state['connected'] = True
    socketio.emit('scanner_connected', {'message': 'Connected to IBKR'})

    try:
        while scanner_state['running']:
            scan_start = time.time()
            scanner_state['scan_count'] += 1

            logger.info(f"Scan #{scanner_state['scan_count']} started")

            all_results = []

            # Scan each symbol
            for symbol in scanner_state['watchlist']:
                if not scanner_state['running']:
                    break

                result = scan_symbol(symbol, components)
                all_results.append(result)

                # Emit real-time update
                socketio.emit('scan_update', result)

                time.sleep(1)  # Brief pause between symbols

            # Update state
            scanner_state['current_signals'] = all_results
            scanner_state['last_scan'] = datetime.now().isoformat()

            # Add to recent scans
            scanner_state['recent_scans'].insert(0, {
                'timestamp': datetime.now().isoformat(),
                'scan_number': scanner_state['scan_count'],
                'symbols_scanned': len(all_results),
                'total_signals': sum(len(r['signals']) for r in all_results)
            })
            scanner_state['recent_scans'] = scanner_state['recent_scans'][:20]  # Keep last 20

            # Emit scan complete
            scan_duration = time.time() - scan_start
            socketio.emit('scan_complete', {
                'scan_number': scanner_state['scan_count'],
                'duration': scan_duration,
                'results': all_results
            })

            # Wait for next scan
            scan_interval = config['scanning']['interval_seconds']
            wait_time = max(0, scan_interval - scan_duration)

            if wait_time > 0 and scanner_state['running']:
                logger.info(f"Waiting {wait_time:.0f} seconds until next scan...")
                time.sleep(wait_time)

    except Exception as e:
        logger.error(f"Scanner worker error: {e}", exc_info=True)
        socketio.emit('scanner_error', {'message': str(e)})
    finally:
        components['ibkr'].disconnect()
        scanner_state['connected'] = False
        scanner_state['running'] = False
        logger.info("Scanner worker stopped")


# ===== Flask Routes =====

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get scanner status"""
    return jsonify({
        'running': scanner_state['running'],
        'connected': scanner_state['connected'],
        'scan_count': scanner_state['scan_count'],
        'last_scan': scanner_state['last_scan'],
        'watchlist': scanner_state['watchlist']
    })


@app.route('/api/signals')
def get_signals():
    """Get current signals"""
    return jsonify(scanner_state['current_signals'])


@app.route('/api/config')
def get_config():
    """Get configuration"""
    config = load_config()
    return jsonify(config) if config else jsonify({'error': 'Failed to load config'}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        new_config = request.json

        # Save to file
        with open('config.yaml', 'w') as f:
            yaml.dump(new_config, f)

        # Reload config
        load_config()

        return jsonify({'success': True, 'message': 'Configuration updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """Get watchlist"""
    return jsonify(scanner_state['watchlist'])


@app.route('/api/watchlist', methods=['POST'])
def update_watchlist():
    """Update watchlist"""
    try:
        new_watchlist = request.json.get('symbols', [])
        scanner_state['watchlist'] = new_watchlist

        # Update config file
        config = load_config()
        config['watchlist']['symbols'] = new_watchlist

        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

        return jsonify({'success': True, 'watchlist': new_watchlist})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/<symbol>')
def get_symbol_history(symbol):
    """Get historical data for a symbol"""
    try:
        config = load_config()
        storage = DataStorage(config)
        history = storage.get_historical_metrics(symbol, days=30)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recent_scans')
def get_recent_scans():
    """Get recent scan history"""
    return jsonify(scanner_state['recent_scans'])


# ===== SocketIO Events =====

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected")
    emit('status', {
        'running': scanner_state['running'],
        'connected': scanner_state['connected']
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")


@socketio.on('start_scanner')
def handle_start_scanner():
    """Start the scanner"""
    global scanner_thread

    with scanner_lock:
        if scanner_state['running']:
            emit('error', {'message': 'Scanner already running'})
            return

        scanner_state['running'] = True

        # Start scanner thread
        scanner_thread = threading.Thread(target=scanner_worker, daemon=True)
        scanner_thread.start()

        emit('scanner_started', {'message': 'Scanner started'})
        logger.info("Scanner started via web UI")


@socketio.on('stop_scanner')
def handle_stop_scanner():
    """Stop the scanner"""
    with scanner_lock:
        if not scanner_state['running']:
            emit('error', {'message': 'Scanner not running'})
            return

        scanner_state['running'] = False
        emit('scanner_stopped', {'message': 'Scanner stopped'})
        logger.info("Scanner stopped via web UI")


@socketio.on('scan_once')
def handle_scan_once(data):
    """Trigger a single scan"""
    try:
        symbol = data.get('symbol', 'SPY')

        config = load_config()
        components = init_scanner_components(config)

        if not components['ibkr'].connect():
            emit('error', {'message': 'Failed to connect to IBKR'})
            return

        result = scan_symbol(symbol, components)
        components['ibkr'].disconnect()

        emit('scan_result', result)

    except Exception as e:
        emit('error', {'message': str(e)})


def main():
    """Run the web application"""
    print("\n" + "="*80)
    print("🐋 WHALE OPTIONS SCANNER - WEB UI")
    print("="*80)
    print("\n📊 Dashboard: http://localhost:5000")
    print("\n⚠️  Make sure IBKR TWS/Gateway is running before starting scanner!")
    print("\n" + "="*80 + "\n")

    # Load initial config
    load_config()

    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
