"""
Whale Scanner REST API
Flask REST API for managing tickers, rules, and viewing signals
"""

import os
import logging
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading

from database_storage import DatabaseStorage
from whale_scanner import WhaleScanner, ScannerConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize database
db = DatabaseStorage()

# Scanner state
scanner_state = {
    'running': False,
    'scanner': None,
    'thread': None,
    'last_scan': None
}


# =============================================================================
# DASHBOARD
# =============================================================================

@app.route('/')
def dashboard():
    """Serve dashboard page"""
    return render_template('whale_dashboard.html')


@app.route('/rules')
def rules_config():
    """Serve rule configuration page"""
    return render_template('rule_config.html')


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected'
    })


@app.route('/api/status')
def get_status():
    """Get scanner status"""
    return jsonify({
        'scanner_running': scanner_state['running'],
        'last_scan': scanner_state['last_scan']
    })


# =============================================================================
# TICKERS
# =============================================================================

@app.route('/api/tickers', methods=['GET'])
def get_tickers():
    """Get all active tickers"""
    try:
        tickers = db.get_active_tickers()
        return jsonify({'tickers': tickers})
    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickers', methods=['POST'])
def add_ticker():
    """Add new ticker to watchlist"""
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()

        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400

        ticker_id = db.add_ticker(
            symbol=symbol,
            name=data.get('name'),
            sector=data.get('sector'),
            notes=data.get('notes')
        )

        return jsonify({
            'message': f'Ticker {symbol} added',
            'ticker_id': ticker_id
        })

    except Exception as e:
        logger.error(f"Error adding ticker: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tickers/<symbol>', methods=['DELETE'])
def remove_ticker(symbol):
    """Remove ticker from watchlist"""
    try:
        success = db.remove_ticker(symbol.upper())

        if success:
            return jsonify({'message': f'Ticker {symbol} removed'})
        else:
            return jsonify({'error': 'Ticker not found'}), 404

    except Exception as e:
        logger.error(f"Error removing ticker: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# WHALE RULES
# =============================================================================

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """Get all active whale rules"""
    try:
        rule_type = request.args.get('type')  # FILTER, SIGNAL, COMBO
        rules = db.get_active_rules(rule_type=rule_type)
        return jsonify({'rules': rules})
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules/<rule_name>', methods=['GET'])
def get_rule(rule_name):
    """Get specific rule"""
    try:
        rule = db.get_rule_by_name(rule_name)

        if rule:
            return jsonify({'rule': rule})
        else:
            return jsonify({'error': 'Rule not found'}), 404

    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules/<rule_name>', methods=['PUT'])
def update_rule(rule_name):
    """Update rule configuration"""
    try:
        data = request.json
        config = data.get('config')

        if not config:
            return jsonify({'error': 'Configuration required'}), 400

        success = db.update_rule_config(rule_name, config)

        if success:
            return jsonify({'message': f'Rule {rule_name} updated'})
        else:
            return jsonify({'error': 'Rule not found'}), 404

    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules/<rule_name>/toggle', methods=['POST'])
def toggle_rule(rule_name):
    """Enable or disable a rule"""
    try:
        data = request.json
        is_active = data.get('is_active', True)

        success = db.toggle_rule(rule_name, is_active)

        if success:
            status = 'enabled' if is_active else 'disabled'
            return jsonify({'message': f'Rule {rule_name} {status}'})
        else:
            return jsonify({'error': 'Rule not found'}), 404

    except Exception as e:
        logger.error(f"Error toggling rule: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SIGNALS
# =============================================================================

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get active whale signals"""
    try:
        symbol = request.args.get('symbol')
        signals = db.get_active_signals(symbol=symbol.upper() if symbol else None)
        return jsonify({'signals': signals})
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# DASHBOARD
# =============================================================================

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get watchlist dashboard data"""
    try:
        watchlist = db.get_watchlist_dashboard()
        return jsonify({'watchlist': watchlist})
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scans/recent', methods=['GET'])
def get_recent_scans():
    """Get recent scan runs"""
    try:
        limit = request.args.get('limit', 10, type=int)
        scans = db.get_recent_scans(limit=limit)
        return jsonify({'scans': scans})
    except Exception as e:
        logger.error(f"Error getting recent scans: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SCANNER CONTROL
# =============================================================================

@app.route('/api/scanner/start', methods=['POST'])
def start_scanner():
    """Start continuous scanner"""
    try:
        if scanner_state['running']:
            return jsonify({'error': 'Scanner already running'}), 400

        # Get configuration
        data = request.json or {}
        config = ScannerConfig(
            scan_interval=data.get('interval', 60),
            max_expirations=data.get('max_expirations', 5)
        )

        # Create scanner
        scanner = WhaleScanner(config=config)
        scanner_state['scanner'] = scanner

        # Start in background thread
        def run_scanner():
            try:
                scanner.run_continuous()
            except Exception as e:
                logger.error(f"Scanner error: {e}")
            finally:
                scanner_state['running'] = False
                scanner_state['scanner'] = None

        thread = threading.Thread(target=run_scanner, daemon=True)
        thread.start()

        scanner_state['running'] = True
        scanner_state['thread'] = thread

        return jsonify({'message': 'Scanner started'})

    except Exception as e:
        logger.error(f"Error starting scanner: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scanner/stop', methods=['POST'])
def stop_scanner():
    """Stop continuous scanner"""
    try:
        if not scanner_state['running']:
            return jsonify({'error': 'Scanner not running'}), 400

        # Stop scanner
        if scanner_state['scanner']:
            scanner_state['scanner'].stop()

        scanner_state['running'] = False
        scanner_state['scanner'] = None

        return jsonify({'message': 'Scanner stopped'})

    except Exception as e:
        logger.error(f"Error stopping scanner: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scanner/run-once', methods=['POST'])
def run_scanner_once():
    """Run scanner once"""
    try:
        if scanner_state['running']:
            return jsonify({'error': 'Scanner already running'}), 400

        # Create scanner
        scanner = WhaleScanner()

        # Run once
        results = scanner.run_once()
        scanner_state['last_scan'] = results

        return jsonify({
            'message': 'Scan complete',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error running scanner: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run Flask server"""
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))

    logger.info(f"Starting Whale Scanner API on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
