#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Creates database and tables for whale scanner
"""

import sys
import yaml
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def load_config():
    """Load configuration"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def create_database(config):
    """Create database if it doesn't exist"""
    pg_config = config['postgres']

    print("\n" + "=" * 60)
    print("PostgreSQL Database Setup")
    print("=" * 60)

    # Connect to postgres database to create our database
    print(f"\n1. Connecting to PostgreSQL server...")
    try:
        conn = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            user=pg_config['user'],
            password=pg_config['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print(f"   ✓ Connected to PostgreSQL at {pg_config['host']}:{pg_config['port']}")

    except psycopg2.OperationalError as e:
        print(f"   ✗ Connection failed: {e}")
        print("\n   Troubleshooting:")
        print("   - Is PostgreSQL running? (brew services start postgresql)")
        print("   - Is the password correct in config.yaml?")
        print("   - Can you connect manually? (psql -U postgres)")
        sys.exit(1)

    # Check if database exists
    print(f"\n2. Checking if database '{pg_config['database']}' exists...")
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (pg_config['database'],))
    exists = cur.fetchone()

    if exists:
        print(f"   ✓ Database '{pg_config['database']}' already exists")

        response = input(f"\n   Drop and recreate database? (yes/no): ")
        if response.lower() == 'yes':
            print(f"   → Dropping database '{pg_config['database']}'...")
            cur.execute(f"DROP DATABASE {pg_config['database']}")
            print(f"   ✓ Dropped database")
            exists = False

    if not exists:
        print(f"   → Creating database '{pg_config['database']}'...")
        cur.execute(f"CREATE DATABASE {pg_config['database']}")
        print(f"   ✓ Created database '{pg_config['database']}'")

    cur.close()
    conn.close()

    return True

def run_schema(config):
    """Run schema SQL file"""
    pg_config = config['postgres']

    print(f"\n3. Running schema script...")

    # Connect to our database
    try:
        conn = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            user=pg_config['user'],
            password=pg_config['password'],
            database=pg_config['database']
        )
        cur = conn.cursor()

        # Read and execute schema file
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

        if not os.path.exists(schema_path):
            print(f"   ✗ Schema file not found: {schema_path}")
            return False

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        cur.execute(schema_sql)
        conn.commit()

        print(f"   ✓ Schema created successfully")

        # Verify tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]

        print(f"\n4. Created {len(tables)} tables:")
        for table in tables:
            print(f"     - {table}")

        # Verify watchlist
        cur.execute("SELECT COUNT(*) FROM watchlist_symbols")
        count = cur.fetchone()[0]
        print(f"\n5. Watchlist initialized with {count} symbols")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection(config):
    """Test connection and show summary"""
    pg_config = config['postgres']

    print(f"\n6. Testing connection...")

    try:
        conn = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            user=pg_config['user'],
            password=pg_config['password'],
            database=pg_config['database']
        )
        cur = conn.cursor()

        # Get stats
        cur.execute("SELECT COUNT(*) FROM watchlist_symbols WHERE is_active = true")
        active_symbols = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM historical_metrics")
        metrics_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM option_contracts")
        contracts_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM whale_signals")
        signals_count = cur.fetchone()[0]

        print(f"   ✓ Connection successful!")
        print(f"\n   Database Statistics:")
        print(f"   - Active Symbols: {active_symbols}")
        print(f"   - Historical Metrics: {metrics_count}")
        print(f"   - Option Contracts: {contracts_count}")
        print(f"   - Whale Signals: {signals_count}")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        print(f"   ✗ Connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(script_dir))

    print("\n🐋 Whale Scanner - PostgreSQL Setup")

    # Load config
    config = load_config()

    if not config.get('postgres', {}).get('enabled', False):
        print("\n⚠️  PostgreSQL is disabled in config.yaml")
        print("   Set postgres.enabled to true to continue")
        sys.exit(1)

    # Create database
    if not create_database(config):
        sys.exit(1)

    # Run schema
    if not run_schema(config):
        sys.exit(1)

    # Test connection
    if not test_connection(config):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ PostgreSQL Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Update postgres.password in config.yaml if needed")
    print("  2. Run the scanner: python scanner.py")
    print("  3. Or start web UI: python web_app.py")
    print("\nDatabase connection string:")
    pg_config = config['postgres']
    print(f"  postgresql://{pg_config['user']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
