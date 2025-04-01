import os
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import yaml

# Import dotenv library to load .env file
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Import required backend classes
from src.rhosocial.activerecord.backend.typing import ConnectionConfig
from src.rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from src.rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend


def find_config_file(base_name: str) -> Optional[Path]:
    """
    Find configuration file in the config directory.

    Args:
        base_name: Base name of the config file without extension

    Returns:
        Path to the config file or None if not found
    """
    # Get the directory of this conftest.py file
    current_dir = Path(__file__).parent.parent.parent

    # Look for config files with different extensions
    for ext in ['.yml', '.yaml']:
        config_path = current_dir / 'config' / f"{base_name}{ext}"
        if config_path.exists():
            return config_path

    return None


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary with configuration
    """
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config file {file_path}: {e}")
        return {}


def load_environment_variables() -> None:
    """Load environment variables from .env file if available"""
    if HAS_DOTENV:
        env_path = Path(__file__).parent.parent.parent / 'config' / '.env'
        if env_path.exists():
            load_dotenv(env_path)


def load_config() -> Dict[str, Any]:
    """
    Load configuration from files and environment variables.
    Priority (highest to lowest):
    1. Environment variables
    2. Local config file (config.local.yml)
    3. Public config file (config.yml)

    Returns:
        Merged configuration dictionary
    """
    # Start with empty config
    config = {}

    # Load public config (lowest priority)
    public_config_path = find_config_file('config')
    if public_config_path:
        public_config = load_yaml_config(public_config_path)
        config.update(public_config)

    # Load local config (overrides public config)
    local_config_path = find_config_file('config.local')
    if local_config_path:
        local_config = load_yaml_config(local_config_path)
        # Deep merge the configurations
        deep_merge(config, local_config)

    # Load environment variables (highest priority)
    load_environment_variables()

    # Override with environment variables if they exist
    env_vars = {
        'databases.mysql.host': os.environ.get('MYSQL_HOST'),
        'databases.mysql.port': os.environ.get('MYSQL_PORT'),
        'databases.mysql.database': os.environ.get('MYSQL_DATABASE'),
        'databases.mysql.username': os.environ.get('MYSQL_USER'),
        'databases.mysql.password': os.environ.get('MYSQL_PASSWORD'),
        'databases.mariadb.host': os.environ.get('MARIADB_HOST'),
        'databases.mariadb.port': os.environ.get('MARIADB_PORT'),
        'databases.mariadb.database': os.environ.get('MARIADB_DATABASE'),
        'databases.mariadb.username': os.environ.get('MARIADB_USER'),
        'databases.mariadb.password': os.environ.get('MARIADB_PASSWORD'),
        'databases.sqlite.database': os.environ.get('SQLITE_DATABASE'),
    }

    # Apply environment variables if they exist
    for path, value in env_vars.items():
        if value is not None:
            set_nested_value(config, path.split('.'), value)

    return config


# [Deep merge and set_nested_value functions remain the same]

# Load configuration once at module import time
CONFIG = load_config()


def get_mysql_config(version_label: Optional[str] = None) -> ConnectionConfig:
    """
    Get MySQL connection configuration.

    Args:
        version_label: Optional label to select specific MySQL version

    Returns:
        ConnectionConfig object
    """
    if 'databases' not in CONFIG or 'mysql' not in CONFIG['databases']:
        pytest.skip("MySQL configuration not found")

    mysql_config = CONFIG['databases']['mysql'].copy()

    # Find version by label if specified
    version = None
    if version_label and 'versions' in mysql_config:
        for ver_info in mysql_config.get('versions', []):
            if ver_info.get('label') == version_label:
                version = tuple(ver_info.get('version', [0, 0, 0]))
                break

    # Remove versions key as it's not needed in ConnectionConfig
    if 'versions' in mysql_config:
        del mysql_config['versions']

    # Override version if specified
    if version:
        mysql_config['version'] = version

    return ConnectionConfig(**mysql_config)


def get_mariadb_config(version_label: Optional[str] = None) -> ConnectionConfig:
    """
    Get MariaDB connection configuration.

    Args:
        version_label: Optional label to select specific MariaDB version

    Returns:
        ConnectionConfig object
    """
    if 'databases' not in CONFIG or 'mariadb' not in CONFIG['databases']:
        pytest.skip("MariaDB configuration not found")

    mariadb_config = CONFIG['databases']['mariadb'].copy()

    # Find version by label if specified
    version = None
    if version_label and 'versions' in mariadb_config:
        for ver_info in mariadb_config.get('versions', []):
            if ver_info.get('label') == version_label:
                version = tuple(ver_info.get('version', [0, 0, 0]))
                break

    # Remove versions key as it's not needed in ConnectionConfig
    if 'versions' in mariadb_config:
        del mariadb_config['versions']

    # Override version if specified
    if version:
        mariadb_config['version'] = version

    return ConnectionConfig(**mariadb_config)


def get_use_mock_backend() -> bool:
    """
    Determine if tests should use mock backend.

    Returns:
        True if mock backend should be used, False otherwise
    """
    return CONFIG.get('test_settings', {}).get('use_mock_backend', True)


class MockConnection:
    """Mock database connection for testing"""

    def __init__(self, version=(8, 0, 21)):
        self.version = version
        self.executed_queries = []
        self.cursor_mock = None

    def cursor(self, **kwargs):
        """Return mock cursor"""
        import unittest.mock
        self.cursor_mock = unittest.mock.MagicMock()
        return self.cursor_mock

    def commit(self):
        """Mock commit"""
        pass

    def close(self):
        """Mock close"""
        pass


@pytest.fixture
def mysql_backend(request):
    """
    Fixture to provide MySQL backend.

    Args:
        request: Pytest request object to access markers

    Returns:
        MySQLBackend instance
    """
    # Check for version marker
    version_label = None
    for marker in request.node.iter_markers(name="mysql_version"):
        version_label = marker.args[0] if marker.args else None
        break

    config = get_mysql_config(version_label)

    # Check if we should use mock or real connection
    use_mock = get_use_mock_backend()

    if use_mock:
        # Create mock backend
        import unittest.mock
        with unittest.mock.patch('mysql.connector.connect') as mock_connect:
            # Configure mock based on version
            mock_connection = MockConnection(version=config.version or (8, 0, 21))
            mock_connect.return_value = mock_connection

            # Create and return backend
            backend = MySQLBackend(connection_config=config)
            yield backend
    else:
        # Create real backend
        try:
            backend = MySQLBackend(connection_config=config)
            yield backend
        finally:
            # Cleanup
            if hasattr(backend, '_connection') and backend._connection:
                backend.disconnect()


@pytest.fixture
def mariadb_backend(request):
    """
    Fixture to provide MariaDB backend.

    Args:
        request: Pytest request object to access markers

    Returns:
        MariaDBBackend instance
    """
    # Check for version marker
    version_label = None
    for marker in request.node.iter_markers(name="mariadb_version"):
        version_label = marker.args[0] if marker.args else None
        break

    config = get_mariadb_config(version_label)

    # Check if we should use mock or real connection
    use_mock = get_use_mock_backend()

    if use_mock:
        # Create mock backend
        import unittest.mock
        with unittest.mock.patch('mariadb.connect') as mock_connect:
            # Configure mock based on version
            mock_connection = MockConnection(version=config.version or (10, 5, 0))
            mock_connect.return_value = mock_connection

            # Create and return backend
            backend = MariaDBBackend(connection_config=config)
            yield backend
    else:
        # Create real backend
        try:
            backend = MariaDBBackend(connection_config=config)
            yield backend
        finally:
            # Cleanup
            if hasattr(backend, '_connection') and backend._connection:
                backend.disconnect()


# Create markers for database versions
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "mysql_version(label): specify MySQL version label to use"
    )
    config.addinivalue_line(
        "markers", "mariadb_version(label): specify MariaDB version label to use"
    )


# Skip tests marked with version if no matching version found
def pytest_runtest_setup(item):
    """Set up test - skip if appropriate"""
    # Handle MySQL version markers
    for marker in item.iter_markers(name="mysql_version"):
        version_label = marker.args[0] if marker.args else None
        if version_label and version_label != "any":
            mysql_config = CONFIG.get('databases', {}).get('mysql', {})
            versions = mysql_config.get('versions', [])

            # Check if version exists
            version_exists = any(v.get('label') == version_label for v in versions)
            if not version_exists:
                pytest.skip(f"MySQL version with label '{version_label}' not configured")

    # Handle MariaDB version markers
    for marker in item.iter_markers(name="mariadb_version"):
        version_label = marker.args[0] if marker.args else None
        if version_label:
            mariadb_config = CONFIG.get('databases', {}).get('mariadb', {})
            versions = mariadb_config.get('versions', [])

            # Check if version exists
            version_exists = any(v.get('label') == version_label for v in versions)
            if not version_exists:
                pytest.skip(f"MariaDB version with label '{version_label}' not configured")