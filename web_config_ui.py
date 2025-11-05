#!/usr/bin/env python3
"""
Web UI for Whale Scanner Configuration Management

A Flask-based web interface for managing scanner configurations stored in PostgreSQL.
Provides an intuitive UI for viewing, editing, comparing, and activating configuration profiles.

Usage:
    python web_config_ui.py

    Then open browser to: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import yaml
import json
from datetime import datetime
from postgres_storage import PostgresStorage
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'whale-scanner-config-secret-key-change-in-production'

# Load base configuration
def load_base_config():
    """Load base configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config.yaml: {e}")
        return {}

# Initialize storage
base_config = load_base_config()
storage = None

def get_storage():
    """Get or create PostgresStorage instance"""
    global storage
    if storage is None:
        try:
            storage = PostgresStorage(base_config)
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(
                "Cannot connect to PostgreSQL database. "
                "Please ensure PostgreSQL is running and the database is initialized. "
                f"Error: {str(e)}"
            )
    return storage

# Error Handlers

@app.errorhandler(ConnectionError)
def handle_connection_error(e):
    """Handle database connection errors"""
    return render_template('error.html',
                         error_title="Database Connection Error",
                         error_message=str(e),
                         suggestions=[
                             "Start PostgreSQL: brew services start postgresql (macOS) or sudo systemctl start postgresql (Linux)",
                             "Initialize database: python database/setup_postgres.py",
                             "Check config.yaml for correct database settings",
                             "Verify PostgreSQL is listening on localhost:5432"
                         ]), 500

# Routes

@app.route('/')
def index():
    """Main dashboard - list all configurations"""
    try:
        db = get_storage()
        configs = db.list_configurations()
        return render_template('index.html', configs=configs)
    except Exception as e:
        logger.error(f"Error loading configurations: {e}")
        flash(f"Error: {str(e)}", "error")
        return render_template('index.html', configs=[])

@app.route('/config/<profile_name>')
def view_config(profile_name):
    """View a specific configuration"""
    try:
        db = get_storage()
        config = db.get_configuration(profile_name)
        if config:
            # Pretty print the config data
            config['config_json'] = json.dumps(config['config_data'], indent=2)
            return render_template('view_config.html', config=config)
        else:
            flash(f"Configuration '{profile_name}' not found", "error")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error viewing configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/config/<profile_name>/edit', methods=['GET', 'POST'])
def edit_config(profile_name):
    """Edit a configuration"""
    db = get_storage()

    if request.method == 'POST':
        try:
            # Get form data
            config_json = request.form.get('config_data')
            description = request.form.get('description', '')
            is_active = request.form.get('is_active') == 'on'

            # Parse and validate JSON
            config_data = json.loads(config_json)

            # Save to database
            success = db.save_configuration(
                profile_name=profile_name,
                config_data=config_data,
                description=description,
                set_active=is_active
            )

            if success:
                flash(f"Configuration '{profile_name}' saved successfully!", "success")
                return redirect(url_for('view_config', profile_name=profile_name))
            else:
                flash("Failed to save configuration", "error")
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {str(e)}", "error")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            flash(f"Error: {str(e)}", "error")

    # GET request - load config for editing
    try:
        config = db.get_configuration(profile_name)
        if config:
            config['config_json'] = json.dumps(config['config_data'], indent=2)
            return render_template('edit_config.html', config=config)
        else:
            flash(f"Configuration '{profile_name}' not found", "error")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/config/new', methods=['GET', 'POST'])
def new_config():
    """Create a new configuration"""
    db = get_storage()

    if request.method == 'POST':
        try:
            profile_name = request.form.get('profile_name', '').strip()
            config_json = request.form.get('config_data')
            description = request.form.get('description', '')
            is_active = request.form.get('is_active') == 'on'

            if not profile_name:
                flash("Profile name is required", "error")
                return render_template('new_config.html',
                                     config_json=config_json,
                                     description=description)

            # Parse and validate JSON
            config_data = json.loads(config_json)

            # Save to database
            success = db.save_configuration(
                profile_name=profile_name,
                config_data=config_data,
                description=description,
                set_active=is_active
            )

            if success:
                flash(f"Configuration '{profile_name}' created successfully!", "success")
                return redirect(url_for('view_config', profile_name=profile_name))
            else:
                flash("Failed to create configuration", "error")
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {str(e)}", "error")
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            flash(f"Error: {str(e)}", "error")

    # GET request - show form with default config
    try:
        # Use the base config as template
        default_config = base_config.get('whale_filters', {})
        config_json = json.dumps(default_config, indent=2)
        return render_template('new_config.html',
                             config_json=config_json,
                             description='')
    except Exception as e:
        logger.error(f"Error loading default configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/config/<profile_name>/clone', methods=['POST'])
def clone_config(profile_name):
    """Clone a configuration"""
    try:
        new_name = request.form.get('new_profile_name', '').strip()
        if not new_name:
            flash("New profile name is required", "error")
            return redirect(url_for('view_config', profile_name=profile_name))

        db = get_storage()
        success = db.clone_configuration(profile_name, new_name)

        if success:
            flash(f"Configuration cloned to '{new_name}'", "success")
            return redirect(url_for('view_config', profile_name=new_name))
        else:
            flash("Failed to clone configuration", "error")
            return redirect(url_for('view_config', profile_name=profile_name))
    except Exception as e:
        logger.error(f"Error cloning configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('view_config', profile_name=profile_name))

@app.route('/config/<profile_name>/activate', methods=['POST'])
def activate_config(profile_name):
    """Activate a configuration"""
    try:
        db = get_storage()
        success = db.set_active_configuration(profile_name)

        if success:
            flash(f"Configuration '{profile_name}' activated", "success")
        else:
            flash("Failed to activate configuration", "error")

        return redirect(url_for('view_config', profile_name=profile_name))
    except Exception as e:
        logger.error(f"Error activating configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('view_config', profile_name=profile_name))

@app.route('/config/<profile_name>/delete', methods=['POST'])
def delete_config(profile_name):
    """Delete a configuration"""
    try:
        db = get_storage()
        success = db.delete_configuration(profile_name)

        if success:
            flash(f"Configuration '{profile_name}' deleted", "success")
            return redirect(url_for('index'))
        else:
            flash("Failed to delete configuration", "error")
            return redirect(url_for('view_config', profile_name=profile_name))
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('view_config', profile_name=profile_name))

@app.route('/compare')
def compare_configs():
    """Compare two configurations"""
    try:
        profile1 = request.args.get('profile1')
        profile2 = request.args.get('profile2')

        db = get_storage()
        configs = db.list_configurations()

        if not profile1 or not profile2:
            return render_template('compare.html', configs=configs)

        config1 = db.get_configuration(profile1)
        config2 = db.get_configuration(profile2)

        if not config1 or not config2:
            flash("One or both configurations not found", "error")
            return render_template('compare.html', configs=configs)

        # Find differences
        differences = []
        _find_differences(config1['config_data'], config2['config_data'], '', differences)

        return render_template('compare.html',
                             configs=configs,
                             config1=config1,
                             config2=config2,
                             differences=differences)
    except Exception as e:
        logger.error(f"Error comparing configurations: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('index'))

def _find_differences(dict1, dict2, path, differences):
    """Recursively find differences between two dictionaries"""
    all_keys = set(dict1.keys()) | set(dict2.keys())

    for key in sorted(all_keys):
        current_path = f"{path}.{key}" if path else key

        if key not in dict1:
            differences.append({
                'path': current_path,
                'value1': '<missing>',
                'value2': dict2[key]
            })
        elif key not in dict2:
            differences.append({
                'path': current_path,
                'value1': dict1[key],
                'value2': '<missing>'
            })
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            _find_differences(dict1[key], dict2[key], current_path, differences)
        elif dict1[key] != dict2[key]:
            differences.append({
                'path': current_path,
                'value1': dict1[key],
                'value2': dict2[key]
            })

# API Endpoints

@app.route('/api/configs')
def api_list_configs():
    """API: List all configurations"""
    try:
        db = get_storage()
        configs = db.list_configurations()
        return jsonify({'success': True, 'configs': configs})
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/<profile_name>')
def api_get_config(profile_name):
    """API: Get a specific configuration"""
    try:
        db = get_storage()
        config = db.get_configuration(profile_name)
        if config:
            return jsonify({'success': True, 'config': config})
        else:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/<profile_name>', methods=['PUT'])
def api_update_config(profile_name):
    """API: Update a configuration"""
    try:
        data = request.get_json()
        db = get_storage()

        success = db.save_configuration(
            profile_name=profile_name,
            config_data=data.get('config_data'),
            description=data.get('description'),
            set_active=data.get('is_active', False)
        )

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save'}), 500
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Whale Scanner Configuration Web UI")
    print("=" * 60)
    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
