# Database Configuration Management

## Overview

The whale scanner now supports storing **configuration profiles in PostgreSQL**. This allows you to:

✅ **Manage multiple configurations** - Production, testing, aggressive, conservative profiles
✅ **Switch configurations dynamically** - No need to edit config.yaml
✅ **Track configuration history** - See when configs were created/updated
✅ **Share configurations** - Multiple users can access same profiles
✅ **Version control configs** - Clone and modify profiles easily

## Why Database Configurations?

**Traditional (config.yaml):**
- ❌ Must edit file to change settings
- ❌ Hard to manage multiple environments
- ❌ No history of changes
- ❌ Can't share across instances

**Database Configurations:**
- ✅ Switch profiles with one command
- ✅ Manage via CLI or web UI
- ✅ Full change history
- ✅ Shared across all scanner instances
- ✅ Hot-reload without restart (future feature)

## Quick Start

### 1. Enable PostgreSQL

In `config.yaml`:
```yaml
postgres:
  enabled: true
  host: "localhost"
  port: 5432
  database: "whale_scanner"
  user: "postgres"
  password: ""
```

### 2. Setup Database

```bash
python database/setup_postgres.py
```

This creates a `configurations` table and inserts a default profile.

### 3. List Configurations

```bash
python config_manager.py list
```

Output:
```
Configuration Profiles:
→ default    Default whale detection configuration    ✓    2025-11-04 10:00
```

→ indicates the **active** profile that the scanner will use.

### 4. Run Scanner

```bash
python scanner.py
```

The scanner automatically loads the **active** configuration from the database!

Output:
```
✓ Loaded configuration from database: default
Initializing Whale Scanner...
Configuration source: database:default
```

## Managing Configurations

### List All Profiles

```bash
python config_manager.py list
```

Shows all saved profiles with:
- Profile name
- Description
- Active status (✓)
- Creation date
- Creator

### Show Configuration Details

```bash
# Show active configuration
python config_manager.py show

# Show specific profile
python config_manager.py show --profile aggressive
```

Output shows:
- Profile metadata
- Full configuration in JSON format

### Save Current config.yaml

Save your current `config.yaml` as a new database profile:

```bash
python config_manager.py save production "Production whale scanner config"
```

To save and activate immediately:
```bash
python config_manager.py save production "Production config" --activate
```

### Import from File

Import a configuration from a YAML file:

```bash
python config_manager.py import aggressive ./configs/aggressive.yaml "High-risk settings"
```

### Activate a Profile

Switch to a different configuration:

```bash
python config_manager.py activate production
```

The next time scanner starts, it will use this profile!

### Clone a Profile

Copy an existing profile to create variations:

```bash
python config_manager.py clone default testing "Test configuration"
```

Now you can modify the `testing` profile without affecting `default`.

### Export to File

Export a database profile back to YAML file:

```bash
python config_manager.py export production ./production.yaml
```

Useful for:
- Backup
- Sharing with others
- Version control (git)

### Delete a Profile

```bash
python config_manager.py delete testing
```

Asks for confirmation. Use `--force` to skip:
```bash
python config_manager.py delete testing --force
```

## Configuration Profiles Schema

The `configurations` table stores:

| Column | Description |
|--------|-------------|
| profile_name | Unique name (e.g., "production", "aggressive") |
| config_data | Full configuration as JSONB |
| description | Human-readable description |
| is_active | Whether this is the active profile |
| created_at | When created |
| updated_at | When last modified |
| created_by | User who created it |

## Scanner Behavior

### Loading Priority

1. Scanner loads `config.yaml` first (base configuration)
2. If PostgreSQL enabled, loads active database profile
3. Database config **merges with and overrides** file config
4. Scanner uses combined configuration

### Force File Config

To ignore database and use only `config.yaml`:

```python
from scanner import WhaleScanner

scanner = WhaleScanner(use_db_config=False)
```

Or set environment variable:
```bash
export USE_DB_CONFIG=false
python scanner.py
```

### Check Current Config

When scanner starts, it logs:
```
Configuration source: database:production
```

Or:
```
Configuration source: file:config.yaml
```

## Configuration Examples

### Aggressive Profile

High-risk, high-reward settings:

```yaml
whale_filters:
  liquidity_gate:
    min_volume: 250000      # Lower threshold
    min_oi: 50000
  conviction_gate:
    volume_vs_avg_multiplier: 1.5  # More sensitive
```

Save as:
```bash
python config_manager.py import aggressive aggressive.yaml "High-risk whale hunting"
```

### Conservative Profile

Low-risk, high-confidence settings:

```yaml
whale_filters:
  liquidity_gate:
    min_volume: 1000000     # Higher threshold
    min_oi: 200000
  conviction_gate:
    volume_vs_avg_multiplier: 3.0  # Less sensitive
```

Save as:
```bash
python config_manager.py import conservative conservative.yaml "Low-risk, high conviction"
```

### Testing Profile

For development/testing:

```yaml
scanning:
  interval_seconds: 30      # Faster scans
watchlist:
  symbols: ["SPY"]          # Just one symbol
```

## Python API

### Load Configuration

```python
from postgres_storage import PostgresStorage
import yaml

# Load base config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize storage
storage = PostgresStorage(config)

# Get active configuration
active_config = storage.get_configuration()
print(f"Active: {active_config['profile_name']}")

# Get specific configuration
prod_config = storage.get_configuration('production')
print(prod_config['config_data'])

storage.close()
```

### Save Configuration

```python
# Prepare configuration
new_config = {
    'scanning': {
        'interval_seconds': 60
    },
    'whale_filters': {
        # ... your settings
    }
}

# Save to database
storage.save_configuration(
    profile_name='my_profile',
    config_data=new_config,
    description='My custom configuration',
    set_active=True,
    created_by='username'
)
```

### List Configurations

```python
configs = storage.list_configurations()

for config in configs:
    print(f"{config['profile_name']}: {config['description']}")
    if config['is_active']:
        print("  [ACTIVE]")
```

## SQL Queries

### View All Profiles

```sql
SELECT profile_name, description, is_active, created_at
FROM configurations
ORDER BY is_active DESC, profile_name;
```

### Get Active Configuration

```sql
SELECT * FROM configurations WHERE is_active = true;
```

### Update Configuration

```sql
UPDATE configurations
SET config_data = config_data || '{"scanning": {"interval_seconds": 45}}'::jsonb
WHERE profile_name = 'production';
```

### Query Configuration Value

```sql
-- Get scan interval from production config
SELECT config_data->'scanning'->>'interval_seconds' as scan_interval
FROM configurations
WHERE profile_name = 'production';
```

## Web UI Integration

The web UI can be extended to manage configurations:

**Future Features:**
- Dropdown to select active profile
- Edit configurations in browser
- Real-time config switching (no restart)
- Configuration comparison tool

## Best Practices

### 1. Use Descriptive Names

✅ Good: `production`, `testing`, `aggressive_1.5x`, `conservative_safe`
❌ Bad: `config1`, `test`, `new`, `backup2`

### 2. Add Detailed Descriptions

```bash
python config_manager.py save production \
  "Production config - proven settings from 3 months backtesting, 75% win rate"
```

### 3. Version Your Profiles

```bash
python config_manager.py clone production production_v2.0
# Edit production_v2.0
python config_manager.py activate production_v2.0
```

### 4. Backup Before Major Changes

```bash
python config_manager.py export production ./backups/production_$(date +%Y%m%d).yaml
```

### 5. Test Before Production

```bash
# Save and test new config
python config_manager.py save testing_new "Testing new volume thresholds"
python config_manager.py activate testing_new
python scanner.py  # Test it

# If good, promote to production
python config_manager.py clone testing_new production
python config_manager.py activate production
```

## Troubleshooting

### Error: "PostgreSQL is not enabled"

**Problem:** `config.yaml` has `postgres.enabled = false`

**Solution:**
```yaml
postgres:
  enabled: true
```

### Error: "No active database configuration found"

**Problem:** No profile is marked as active

**Solution:**
```bash
python config_manager.py activate default
```

### Scanner Uses config.yaml Instead of Database

**Problem:** Database config not loading

**Check:**
1. PostgreSQL is running
2. Database exists: `psql -d whale_scanner`
3. Active config exists: `python config_manager.py list`
4. No errors in scanner startup logs

### Configuration Not Taking Effect

**Problem:** Changed config but scanner still uses old settings

**Solution:**
1. Verify changes saved: `python config_manager.py show`
2. Restart scanner
3. Check scanner logs for "Configuration source"

## Migration from config.yaml

### Step 1: Save Current Config

```bash
python config_manager.py save from_file "Migrated from config.yaml" --activate
```

### Step 2: Verify

```bash
python config_manager.py show
```

### Step 3: Test

```bash
python scanner.py
# Check: "Configuration source: database:from_file"
```

### Step 4: Create Variations

```bash
python config_manager.py clone from_file aggressive
python config_manager.py clone from_file conservative
```

Now you can modify these profiles independently!

## Advanced Usage

### Dynamic Configuration Updates

```python
# In running scanner (future feature)
def reload_configuration(self):
    """Reload configuration from database without restart"""
    storage = PostgresStorage(self.config)
    db_config = storage.get_configuration()

    if db_config:
        self.config.update(db_config['config_data'])
        self.logger.info(f"Reloaded config: {db_config['profile_name']}")
    storage.close()
```

### Configuration Versioning

```sql
-- Add version column
ALTER TABLE configurations ADD COLUMN version INTEGER DEFAULT 1;

-- Track changes
CREATE TABLE configuration_history (
    id SERIAL PRIMARY KEY,
    profile_name VARCHAR(50),
    config_data JSONB,
    version INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(50)
);
```

### A/B Testing

Run different profiles simultaneously:

```bash
# Terminal 1: Aggressive strategy
python scanner.py --config-profile aggressive

# Terminal 2: Conservative strategy
python scanner.py --config-profile conservative

# Compare results in database
```

## Summary

| Feature | File (config.yaml) | Database |
|---------|-------------------|----------|
| **Setup** | ✅ Simple | ⚙️ Requires PostgreSQL |
| **Multiple Configs** | ❌ Manual editing | ✅ Easy switching |
| **History** | ❌ Manual backup | ✅ Automatic |
| **Sharing** | ⚠️ File transfer | ✅ Database access |
| **Hot Reload** | ❌ Restart needed | ✅ Future feature |
| **Version Control** | ✅ Git | ✅ Database + Git |

## Commands Reference

```bash
# List profiles
python config_manager.py list

# Show profile
python config_manager.py show [--profile NAME]

# Save from config.yaml
python config_manager.py save NAME "Description" [--activate]

# Import from file
python config_manager.py import NAME FILE "Description" [--activate]

# Activate profile
python config_manager.py activate NAME

# Clone profile
python config_manager.py clone SOURCE TARGET ["Description"]

# Export profile
python config_manager.py export NAME OUTPUT_FILE

# Delete profile
python config_manager.py delete NAME [--force]
```

## Next Steps

1. **Setup PostgreSQL**: `python database/setup_postgres.py`
2. **Save your config**: `python config_manager.py save production "My settings"`
3. **Activate it**: `python config_manager.py activate production`
4. **Run scanner**: `python scanner.py`

Your configurations are now managed in the database! 🎉📊
