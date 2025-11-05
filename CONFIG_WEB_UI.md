# Whale Scanner - Configuration Management Web UI

A user-friendly web interface for managing Whale Scanner configuration profiles stored in PostgreSQL.

## Features

- **Dashboard View**: See all configuration profiles at a glance
- **Visual JSON Editor**: Edit configurations with syntax highlighting and validation
- **Configuration Management**:
  - Create new profiles
  - Edit existing profiles
  - Clone profiles for variations
  - Activate/deactivate profiles
  - Delete profiles
  - Compare two profiles side-by-side
- **Real-time Validation**: JSON syntax checking before saving
- **Format Tools**: Auto-format and validate JSON
- **Responsive Design**: Works on desktop, tablet, and mobile

## Quick Start

### 1. Ensure PostgreSQL is Running

```bash
# Check if PostgreSQL is running
pg_isready

# If not running, start it (macOS with Homebrew)
brew services start postgresql@14

# Or on Linux
sudo systemctl start postgresql
```

### 2. Initialize Database (if not already done)

```bash
# Run the database setup script
python database/setup_postgres.py
```

### 3. Start the Web UI

```bash
python web_config_ui.py
```

The server will start on `http://localhost:5000`

### 4. Open in Browser

Open your web browser to: **http://localhost:5000**

## Usage Guide

### Creating a New Configuration

1. Click **"New Config"** in the navigation bar
2. Enter a unique profile name (e.g., `aggressive_scanning`)
3. Add a description (optional but recommended)
4. Edit the JSON configuration in the editor
5. Use **"Format JSON"** to auto-format your configuration
6. Use **"Validate JSON"** to check for errors
7. Check **"Set as active"** if you want to use this immediately
8. Click **"Create Configuration"**

### Editing a Configuration

1. From the Dashboard, click **"Edit"** on any configuration card
2. Modify the JSON in the syntax-highlighted editor
3. Use the format/validate buttons to ensure correctness
4. Save your changes

### Activating a Configuration

The **active** configuration is what the scanner will use when it runs.

**Method 1: From Dashboard**
- Click **"Activate"** button on any configuration card

**Method 2: From View Page**
- Open a configuration, click **"Activate"** button

**Method 3: When Editing**
- Check the **"Set as active configuration"** checkbox when saving

### Cloning a Configuration

Perfect for creating variations:

1. Open the configuration you want to clone
2. Click the **"Clone"** button
3. Enter a new profile name
4. The new profile will be created with identical settings
5. Edit the clone to customize it

### Comparing Configurations

1. Click **"Compare"** in the navigation
2. Select two configurations from the dropdowns
3. Click **"Compare"**
4. View all differences in a side-by-side table

### Deleting a Configuration

1. Open the configuration to delete
2. Click the **"Delete"** button
3. Confirm the deletion

**Warning**: This action cannot be undone!

## JSON Editor Features

The web UI includes a powerful JSON editor with:

- **Syntax Highlighting**: Makes JSON structure easy to read
- **Line Numbers**: Navigate large configurations easily
- **Auto-Formatting**: One-click JSON beautification
- **Validation**: Real-time error detection
- **Bracket Matching**: Auto-close brackets and braces
- **Dark Theme**: Easy on the eyes for long editing sessions

## Configuration Structure

Configurations should include these key sections:

```json
{
  "whale_filters": {
    "liquidity_gate": {
      "min_volume": 500000,
      "min_open_interest": 1000,
      "min_bid_ask_spread": 0.05
    },
    "conviction_gate": {
      "volume_vs_avg_multiplier": 2.0,
      "oi_change_threshold": 0.15
    },
    "unusual_activity_gate": {
      "volume_to_oi_ratio": 1.5,
      "single_trade_size_threshold": 100
    }
  },
  "data_source": {
    "provider": "tradier",
    "expirations": [30, 60, 90],
    "strikes_range": 0.15
  }
}
```

## API Endpoints

The web UI also exposes REST API endpoints:

### List All Configurations
```bash
GET /api/configs
```

### Get Specific Configuration
```bash
GET /api/config/<profile_name>
```

### Update Configuration
```bash
PUT /api/config/<profile_name>
Content-Type: application/json

{
  "config_data": { ... },
  "description": "Updated config",
  "is_active": true
}
```

## Troubleshooting

### Port Already in Use

If you see "Address already in use" error:

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or change the port in web_config_ui.py
app.run(debug=True, host='0.0.0.0', port=8080)  # Use port 8080 instead
```

### Database Connection Error

```bash
# Check PostgreSQL is running
pg_isready

# Check config.yaml has correct database settings
cat config.yaml | grep -A 5 postgres

# Test connection manually
psql -h localhost -U postgres -d whale_scanner
```

### Configuration Not Showing

```bash
# Check configurations exist in database
python config_manager.py list

# If empty, load default configuration
python config_manager.py save default
```

## Security Notes

**For Production Use:**

1. **Change Secret Key**: Update the Flask secret key in `web_config_ui.py`:
   ```python
   app.secret_key = 'your-secure-random-key-here'
   ```

2. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Apache) with SSL

3. **Add Authentication**: Implement user login/authentication

4. **Restrict Access**: Use firewall rules to limit access to trusted IPs

5. **Environment Variables**: Move sensitive config to environment variables

## Integration with Scanner

The scanner automatically loads the **active** configuration from the database:

```bash
# Run scanner with database configuration
python scanner.py

# Output shows which config is loaded:
# INFO - Configuration loaded from database: aggressive_scanning
```

To use file-based configuration instead:

```bash
# Edit scanner.py and set use_db_config=False
scanner = WhaleScanner(config_path="config.yaml", use_db_config=False)
```

## Tips for Best Results

1. **Start with Default**: Clone the `default` profile before making changes
2. **Use Descriptive Names**: Name profiles like `conservative_scanning`, `aggressive_whale_detection`
3. **Add Descriptions**: Document what makes each profile unique
4. **Test First**: Create a `test` profile for experimenting with settings
5. **Compare Often**: Use the compare feature to understand differences
6. **Backup**: Export important profiles using `config_manager.py export`

## Support

For issues or questions:
- Check logs in terminal where `web_config_ui.py` is running
- Review PostgreSQL logs if database errors occur
- Ensure all dependencies are installed: `pip install -r requirements.txt`
