import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest
import yaml

# Setup logger
logger = logging.getLogger("mariadb_test")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Import required backend classes
from src.rhosocial.activerecord.backend.typing import ConnectionConfig
from src.rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend


def find_config_file(config_dir: Path) -> Optional[Path]:
    """
    Find configuration file in the specified directory

    Args:
        config_dir: Configuration file directory

    Returns:
        Configuration file path or None (if not found)
    """
    for ext in ['.yml', '.yaml']:
        config_path = config_dir / f"config{ext}"
        if config_path.exists():
            logger.info(f"Found configuration file: {config_path}")
            return config_path

    logger.warning(f"No configuration file found in {config_dir}")
    return None


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file

    Args:
        file_path: YAML file path

    Returns:
        Configuration dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from {file_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration file {file_path}: {e}")
        return {}


def load_config() -> Dict[str, Any]:
    """
    Load configuration

    Search in priority order:
    1. 'config' subdirectory of current directory
    2. Current directory
    3. 'config' subdirectory of conftest.py directory
    4. conftest.py directory

    Returns:
        Configuration dictionary
    """
    # Try multiple paths
    search_paths = [
        Path.cwd() / 'config',  # 'config' subdirectory of current working directory
        Path.cwd(),  # Current working directory
        Path(__file__).parent / 'config',  # 'config' subdirectory of conftest.py directory
        Path(__file__).parent,  # conftest.py directory
    ]

    # Find configuration file
    config_file = None
    for path in search_paths:
        config_file = find_config_file(path)
        if config_file:
            break

    # Load configuration file or use default configuration
    if config_file:
        return load_yaml_config(config_file)
    else:
        logger.warning("Configuration file not found, using default configuration")
        return {
            'databases': {
                'mariadb': {
                    'versions': [
                        {'label': 'mariadb105', 'version': [10, 5, 0], 'host': '127.0.0.1', 'port': 3307,
                         'database': 'test', 'username': 'root', 'password': ''},
                    ]
                }
            }
        }


# Load configuration when the module is imported
CONFIG = load_config()


def get_mariadb_versions() -> List[Dict[str, Any]]:
    """
    Get all configured MariaDB versions

    Returns:
        MariaDB version configuration list
    """
    try:
        return CONFIG.get('databases', {}).get('mariadb', {}).get('versions', [])
    except:
        return []


def create_mariadb_connection_config(version_config: Dict[str, Any]) -> ConnectionConfig:
    """
    Create ConnectionConfig based on version configuration

    Args:
        version_config: Version configuration dictionary

    Returns:
        ConnectionConfig object
    """
    # Extract basic connection information
    config_dict = {
        'host': version_config.get('host', '127.0.0.1'),
        'port': version_config.get('port', 3307),
        'database': version_config.get('database', 'test'),
        'username': version_config.get('username', 'root'),
        'password': version_config.get('password', ''),
        'version': tuple(version_config.get('version', [0, 0, 0])),
    }

    # Extract other optional parameters
    for key in ['charset', 'timezone', 'pool_size', 'pool_timeout', 'pool_name',
                'ssl_ca', 'ssl_cert', 'ssl_key', 'ssl_mode', 'auth_plugin']:
        if key in version_config:
            config_dict[key] = version_config[key]

    return ConnectionConfig(**config_dict)


# Parameterized fixture for MariaDB versions
@pytest.fixture(params=get_mariadb_versions(), ids=lambda v: v.get('label', f"mariadb-{v.get('version', [0, 0, 0])}"))
def mariadb_config(request):
    """
    Fixture providing MariaDB connection configuration, executed once for each configured version

    Args:
        request: Pytest request object for accessing parameters

    Returns:
        ConnectionConfig object
    """
    version_config = request.param
    logger.info(f"Using MariaDB configuration: {version_config.get('label')}, version: {version_config.get('version')}")
    return create_mariadb_connection_config(version_config)


@pytest.fixture
def mariadb_connection(mariadb_config):
    """
    Fixture providing MariaDB connection

    Args:
        mariadb_config: MariaDB connection configuration

    Returns:
        MariaDBBackend instance
    """
    logger.info(f"Creating MariaDB connection: {mariadb_config.host}:{mariadb_config.port}")
    backend = MariaDBBackend(connection_config=mariadb_config)

    try:
        backend.connect()
        logger.info("MariaDB connection created successfully")
        yield backend
    finally:
        # Ensure proper cleanup
        if backend:
            logger.info("Cleaning up MariaDB connection")
            # Roll back any active transactions
            if hasattr(backend, '_transaction_manager') and backend._transaction_manager and backend._transaction_manager.is_active:
                logger.warning("Active transaction detected during cleanup, rolling back")
                try:
                    backend._transaction_manager.rollback()
                except Exception as e:
                    logger.error(f"Transaction rollback error: {e}")

            # Disconnect properly
            if hasattr(backend, '_connection') and backend._connection:
                logger.info("Disconnecting MariaDB connection")
                try:
                    backend.disconnect()
                except Exception as e:
                    logger.error(f"Disconnect error: {e}")


@pytest.fixture
def mariadb_test_db(mariadb_connection):
    """
    Fixture to setup and teardown test database

    Args:
        mariadb_connection: MariaDB connection

    Returns:
        MariaDB connection with prepared test tables
    """
    # Import setup and teardown functions from test_crud.py
    try:
        # Try direct import
        from test_mariadb_crud import setup_test_table, teardown_test_table
    except ImportError:
        # If import fails, try dynamic module loading
        import importlib.util
        import sys

        # Find test_mariadb_crud.py file
        for search_path in [Path.cwd(), Path(__file__).parent]:
            module_path = search_path / 'test_mariadb_crud.py'
            if module_path.exists():
                logger.info(f"Found test_mariadb_crud.py: {module_path}")
                spec = importlib.util.spec_from_file_location("test_mariadb_crud", module_path)
                test_crud_module = importlib.util.module_from_spec(spec)
                sys.modules["test_mariadb_crud"] = test_crud_module
                spec.loader.exec_module(test_crud_module)
                setup_test_table = test_crud_module.setup_test_table
                teardown_test_table = test_crud_module.teardown_test_table
                break
        else:
            pytest.skip("Could not find test_mariadb_crud.py module")

    logger.info("Setting up test tables")
    # Ensure starting from a clean state
    if not mariadb_connection._connection:
        mariadb_connection.connect()
    elif hasattr(mariadb_connection,
                 '_transaction_manager') and mariadb_connection._transaction_manager and mariadb_connection._transaction_manager.is_active:
        # If there's an active transaction, roll back first
        try:
            mariadb_connection._transaction_manager.rollback()
            logger.info("Rolled back previous active transaction")
        except Exception as e:
            logger.error(f"Error rolling back previous transaction: {e}")
            # Reconnect on connection error
            mariadb_connection.disconnect()
            mariadb_connection.connect()
            logger.info("Reconnected after transaction error")

    # Setup test tables
    setup_test_table(mariadb_connection)
    logger.info("Test tables created successfully")

    # Return connection for tests to use
    yield mariadb_connection

    # Cleanup after tests
    logger.info("Cleaning up test tables")
    teardown_test_table(mariadb_connection)
    logger.info("Test tables deleted successfully")


def pytest_configure(config):
    """Configure pytest"""
    # No special markers needed as we use parameterized fixtures
    pass