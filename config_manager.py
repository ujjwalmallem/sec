#!/usr/bin/env python3
"""
Configuration Manager - CLI tool for managing scanner configurations in PostgreSQL
"""

import sys
import yaml
import json
import argparse
import os
import tempfile
import subprocess
from datetime import datetime
from postgres_storage import PostgresStorage
from tabulate import tabulate


def load_base_config():
    """Load base configuration to get DB connection"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        sys.exit(1)


def list_configurations(storage):
    """List all configuration profiles"""
    configs = storage.list_configurations()

    if not configs:
        print("No configuration profiles found.")
        return

    # Format for display
    table_data = []
    for config in configs:
        table_data.append([
            "→ " + config['profile_name'] if config['is_active'] else "  " + config['profile_name'],
            config['description'] or '',
            "✓" if config['is_active'] else "",
            config['created_at'].strftime('%Y-%m-%d %H:%M') if config['created_at'] else '',
            config['created_by'] or ''
        ])

    print("\nConfiguration Profiles:")
    print(tabulate(table_data, headers=['Profile Name', 'Description', 'Active', 'Created', 'Created By']))
    print("\n→ indicates active profile")


def show_configuration(storage, profile_name):
    """Show configuration details"""
    config = storage.get_configuration(profile_name)

    if not config:
        print(f"Configuration profile '{profile_name}' not found.")
        return

    print(f"\nProfile: {config['profile_name']}")
    print(f"Description: {config['description'] or 'N/A'}")
    print(f"Active: {'Yes' if config['is_active'] else 'No'}")
    print(f"Created: {config['created_at']}")
    print(f"Updated: {config['updated_at']}")
    print(f"Created By: {config['created_by'] or 'N/A'}")
    print("\nConfiguration Data:")
    print(json.dumps(config['config_data'], indent=2))


def save_configuration_from_file(storage, profile_name, file_path, description, set_active):
    """Save configuration from YAML file"""
    try:
        with open(file_path, 'r') as f:
            config_data = yaml.safe_load(f)

        success = storage.save_configuration(
            profile_name,
            config_data,
            description,
            set_active
        )

        if success:
            print(f"✓ Saved configuration profile: {profile_name}")
            if set_active:
                print(f"✓ Set as active profile")
        else:
            print(f"✗ Failed to save configuration")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def save_configuration_from_current(storage, profile_name, description, set_active):
    """Save current config.yaml as a new profile"""
    try:
        with open('config.yaml', 'r') as f:
            config_data = yaml.safe_load(f)

        success = storage.save_configuration(
            profile_name,
            config_data,
            description,
            set_active
        )

        if success:
            print(f"✓ Saved current configuration as profile: {profile_name}")
            if set_active:
                print(f"✓ Set as active profile")
        else:
            print(f"✗ Failed to save configuration")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def activate_configuration(storage, profile_name):
    """Set a configuration profile as active"""
    success = storage.set_active_configuration(profile_name)

    if success:
        print(f"✓ Activated configuration profile: {profile_name}")
    else:
        print(f"✗ Failed to activate profile (does it exist?)")
        sys.exit(1)


def delete_configuration(storage, profile_name, force=False):
    """Delete a configuration profile"""
    if not force:
        response = input(f"Delete configuration profile '{profile_name}'? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

    success = storage.delete_configuration(profile_name)

    if success:
        print(f"✓ Deleted configuration profile: {profile_name}")
    else:
        print(f"✗ Failed to delete profile (does it exist?)")
        sys.exit(1)


def clone_configuration(storage, source, target, description):
    """Clone a configuration profile"""
    success = storage.clone_configuration(source, target, description)

    if success:
        print(f"✓ Cloned '{source}' to '{target}'")
    else:
        print(f"✗ Failed to clone configuration")
        sys.exit(1)


def export_configuration(storage, profile_name, output_file):
    """Export configuration profile to YAML file"""
    config = storage.get_configuration(profile_name)

    if not config:
        print(f"Configuration profile '{profile_name}' not found.")
        sys.exit(1)

    try:
        with open(output_file, 'w') as f:
            yaml.dump(config['config_data'], f, default_flow_style=False, sort_keys=False)

        print(f"✓ Exported '{profile_name}' to {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def edit_configuration(storage, profile_name):
    """Edit configuration in text editor"""
    config = storage.get_configuration(profile_name)

    if not config:
        print(f"Configuration profile '{profile_name}' not found.")
        sys.exit(1)

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
        yaml.dump(config['config_data'], tf, default_flow_style=False, sort_keys=False)
        temp_path = tf.name

    try:
        # Get editor from environment or use default
        editor = os.environ.get('EDITOR', 'vi')

        # Open editor
        print(f"Opening {profile_name} in {editor}...")
        subprocess.call([editor, temp_path])

        # Read back edited content
        with open(temp_path, 'r') as f:
            edited_config = yaml.safe_load(f)

        # Ask for confirmation
        print("\nConfiguration has been edited.")
        response = input(f"Save changes to '{profile_name}'? (yes/no): ")

        if response.lower() == 'yes':
            # Save updated configuration
            success = storage.save_configuration(
                profile_name,
                edited_config,
                config.get('description'),
                config.get('is_active', False)
            )

            if success:
                print(f"✓ Updated configuration: {profile_name}")
            else:
                print(f"✗ Failed to save configuration")
                sys.exit(1)
        else:
            print("Changes discarded.")

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def set_config_value(storage, profile_name, key_path, value):
    """Set a specific value in configuration"""
    config = storage.get_configuration(profile_name)

    if not config:
        print(f"Configuration profile '{profile_name}' not found.")
        sys.exit(1)

    # Parse key path (e.g., "whale_filters.liquidity_gate.min_volume")
    keys = key_path.split('.')
    config_data = config['config_data']

    # Navigate to the nested key
    current = config_data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the value
    final_key = keys[-1]
    old_value = current.get(final_key, 'N/A')

    # Try to convert value to appropriate type
    try:
        # Try as int
        if value.isdigit():
            new_value = int(value)
        # Try as float
        elif '.' in value and value.replace('.', '').isdigit():
            new_value = float(value)
        # Try as boolean
        elif value.lower() in ('true', 'false'):
            new_value = value.lower() == 'true'
        # Try as JSON
        elif value.startswith('[') or value.startswith('{'):
            new_value = json.loads(value)
        else:
            new_value = value
    except:
        new_value = value

    current[final_key] = new_value

    print(f"\nChanging {key_path}:")
    print(f"  Old value: {old_value}")
    print(f"  New value: {new_value}")

    response = input(f"\nSave changes to '{profile_name}'? (yes/no): ")

    if response.lower() == 'yes':
        success = storage.save_configuration(
            profile_name,
            config_data,
            config.get('description'),
            config.get('is_active', False)
        )

        if success:
            print(f"✓ Updated {key_path} in {profile_name}")
        else:
            print(f"✗ Failed to update configuration")
            sys.exit(1)
    else:
        print("Changes discarded.")


def get_config_value(storage, profile_name, key_path):
    """Get a specific value from configuration"""
    config = storage.get_configuration(profile_name)

    if not config:
        print(f"Configuration profile '{profile_name}' not found.")
        sys.exit(1)

    # Parse key path
    keys = key_path.split('.')
    config_data = config['config_data']

    # Navigate to the value
    current = config_data
    try:
        for key in keys:
            current = current[key]

        print(f"\n{profile_name}.{key_path}:")
        if isinstance(current, dict):
            print(yaml.dump(current, default_flow_style=False))
        else:
            print(f"  {current}")

    except (KeyError, TypeError):
        print(f"Key path '{key_path}' not found in {profile_name}")
        sys.exit(1)


def diff_configurations(storage, profile1, profile2):
    """Compare two configuration profiles"""
    config1 = storage.get_configuration(profile1)
    config2 = storage.get_configuration(profile2)

    if not config1:
        print(f"Configuration profile '{profile1}' not found.")
        sys.exit(1)

    if not config2:
        print(f"Configuration profile '{profile2}' not found.")
        sys.exit(1)

    print(f"\nComparing: {profile1} vs {profile2}\n")
    print("=" * 60)

    # Find differences
    differences = []
    _find_differences(config1['config_data'], config2['config_data'], '', differences)

    if not differences:
        print("✓ Configurations are identical")
    else:
        print(f"Found {len(differences)} difference(s):\n")
        for diff in differences:
            print(f"  {diff['path']}:")
            print(f"    {profile1}: {diff['value1']}")
            print(f"    {profile2}: {diff['value2']}")
            print()


def _find_differences(dict1, dict2, path, differences):
    """Recursively find differences between two dictionaries"""
    # Check keys in dict1
    for key in dict1:
        current_path = f"{path}.{key}" if path else key

        if key not in dict2:
            differences.append({
                'path': current_path,
                'value1': dict1[key],
                'value2': 'N/A'
            })
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            _find_differences(dict1[key], dict2[key], current_path, differences)
        elif dict1[key] != dict2[key]:
            differences.append({
                'path': current_path,
                'value1': dict1[key],
                'value2': dict2[key]
            })

    # Check keys only in dict2
    for key in dict2:
        if key not in dict1:
            current_path = f"{path}.{key}" if path else key
            differences.append({
                'path': current_path,
                'value1': 'N/A',
                'value2': dict2[key]
            })


def main():
    parser = argparse.ArgumentParser(
        description='Manage scanner configuration profiles in PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # List all profiles
  python config_manager.py list

  # Show active profile
  python config_manager.py show

  # Show specific profile
  python config_manager.py show --profile aggressive

  # Save current config.yaml as new profile
  python config_manager.py save production "Production settings"

  # Save and activate
  python config_manager.py save production "Production settings" --activate

  # Import from file
  python config_manager.py import aggressive ./configs/aggressive.yaml "High-risk settings"

  # Activate a profile
  python config_manager.py activate production

  # Clone a profile
  python config_manager.py clone default testing "Test configuration"

  # Export profile to file
  python config_manager.py export production ./production.yaml

  # Delete a profile
  python config_manager.py delete testing

  # Edit a profile interactively
  python config_manager.py edit production

  # Set a specific value
  python config_manager.py set production whale_filters.liquidity_gate.min_volume 750000

  # Get a specific value
  python config_manager.py get production whale_filters.liquidity_gate.min_volume

  # Compare two profiles
  python config_manager.py diff default aggressive
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all configuration profiles')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show configuration details')
    show_parser.add_argument('--profile', help='Profile name (shows active if not specified)')

    # Save command
    save_parser = subparsers.add_parser('save', help='Save current config.yaml as a new profile')
    save_parser.add_argument('profile', help='Profile name')
    save_parser.add_argument('description', help='Profile description')
    save_parser.add_argument('--activate', action='store_true', help='Set as active profile')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration from YAML file')
    import_parser.add_argument('profile', help='Profile name')
    import_parser.add_argument('file', help='YAML file path')
    import_parser.add_argument('description', help='Profile description')
    import_parser.add_argument('--activate', action='store_true', help='Set as active profile')

    # Activate command
    activate_parser = subparsers.add_parser('activate', help='Set a profile as active')
    activate_parser.add_argument('profile', help='Profile name')

    # Clone command
    clone_parser = subparsers.add_parser('clone', help='Clone a configuration profile')
    clone_parser.add_argument('source', help='Source profile name')
    clone_parser.add_argument('target', help='Target profile name')
    clone_parser.add_argument('description', nargs='?', help='Optional description')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export profile to YAML file')
    export_parser.add_argument('profile', help='Profile name')
    export_parser.add_argument('output', help='Output file path')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a configuration profile')
    delete_parser.add_argument('profile', help='Profile name')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')

    # Edit command
    edit_parser = subparsers.add_parser('edit', help='Edit configuration in text editor')
    edit_parser.add_argument('profile', help='Profile name')

    # Set command
    set_parser = subparsers.add_parser('set', help='Set a specific configuration value')
    set_parser.add_argument('profile', help='Profile name')
    set_parser.add_argument('key', help='Key path (e.g., whale_filters.liquidity_gate.min_volume)')
    set_parser.add_argument('value', help='New value')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get a specific configuration value')
    get_parser.add_argument('profile', help='Profile name')
    get_parser.add_argument('key', help='Key path (e.g., whale_filters.liquidity_gate.min_volume)')

    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two configuration profiles')
    diff_parser.add_argument('profile1', help='First profile name')
    diff_parser.add_argument('profile2', help='Second profile name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load base config and initialize storage
    config = load_base_config()

    if not config.get('postgres', {}).get('enabled', False):
        print("Error: PostgreSQL is not enabled in config.yaml")
        print("Set postgres.enabled = true to use configuration management")
        sys.exit(1)

    storage = PostgresStorage(config)

    # Execute command
    try:
        if args.command == 'list':
            list_configurations(storage)

        elif args.command == 'show':
            show_configuration(storage, args.profile)

        elif args.command == 'save':
            save_configuration_from_current(storage, args.profile, args.description, args.activate)

        elif args.command == 'import':
            save_configuration_from_file(storage, args.profile, args.file, args.description, args.activate)

        elif args.command == 'activate':
            activate_configuration(storage, args.profile)

        elif args.command == 'clone':
            clone_configuration(storage, args.source, args.target, args.description)

        elif args.command == 'export':
            export_configuration(storage, args.profile, args.output)

        elif args.command == 'delete':
            delete_configuration(storage, args.profile, args.force)

        elif args.command == 'edit':
            edit_configuration(storage, args.profile)

        elif args.command == 'set':
            set_config_value(storage, args.profile, args.key, args.value)

        elif args.command == 'get':
            get_config_value(storage, args.profile, args.key)

        elif args.command == 'diff':
            diff_configurations(storage, args.profile1, args.profile2)

    finally:
        storage.close()


if __name__ == "__main__":
    main()
