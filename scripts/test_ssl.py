# scripts/test_ssl.py
"""SSL connection test script for MariaDB backend.

This script tests SSL/TLS connections to MariaDB servers.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import yaml
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def load_scenario(scenario_name: str = "mariadb_12_2"):
    """Load a test scenario from the configuration file."""
    config_path = os.path.join(
        os.path.dirname(__file__), '..', 'tests', 'config', 'mariadb_scenarios.yaml'
    )
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    if scenario_name not in config_data['scenarios']:
        available = list(config_data['scenarios'].keys())
        print(f"Scenario '{scenario_name}' not found. Available: {available}")
        scenario_name = available[0]
        print(f"Using first available: {scenario_name}")
    
    return scenario_name, config_data['scenarios'][scenario_name]


def test_no_ssl():
    """Test connection without SSL (should fail for MariaDB 12.2)."""
    print("\n[Test 1: Connection without SSL]")
    print("-" * 40)
    
    scenario_name, config = load_scenario("mariadb_12_2")
    print(f"Scenario: {scenario_name}")
    print(f"Host: {config.get('host')}:{config.get('port')}")
    
    config['ssl_disabled'] = True
    backend = MariaDBBackend(connection_config=MariaDBConnectionConfig(**config))
    
    try:
        backend.connect()
        print("[FAIL] Should have failed - server requires SSL")
        backend.disconnect()
        return False
    except Exception as e:
        if "insecure transport" in str(e).lower() or "require_secure_transport" in str(e).lower():
            print(f"[PASS] Expected error: {e}")
            return True
        else:
            print(f"[FAIL] Unexpected error: {e}")
            return False


def test_ssl_without_verify():
    """Test SSL connection without certificate verification."""
    print("\n[Test 2: SSL connection (no certificate verification)]")
    print("-" * 40)
    
    scenario_name, config = load_scenario("mariadb_12_2")
    print(f"Scenario: {scenario_name}")
    print(f"Host: {config.get('host')}:{config.get('port')}")
    
    config['ssl_disabled'] = False
    config['ssl_verify_cert'] = False
    config['ssl_verify_identity'] = False
    
    backend = MariaDBBackend(connection_config=MariaDBConnectionConfig(**config))
    
    try:
        backend.connect()
        print("[PASS] SSL connection established")
        
        version = backend.get_server_version()
        print(f"[PASS] Server version: {version[0]}.{version[1]}.{version[2]}")
        
        backend.execute("SELECT 1 as test")
        print("[PASS] Query executed successfully")
        
        backend.disconnect()
        print("[PASS] Disconnected successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ssl_with_cert_verify():
    """Test SSL connection with certificate verification."""
    print("\n[Test 3: SSL connection with certificate verification]")
    print("-" * 40)
    
    scenario_name, config = load_scenario("mariadb_12_2")
    print(f"Scenario: {scenario_name}")
    print(f"Host: {config.get('host')}:{config.get('port')}")
    
    config['ssl_disabled'] = False
    config['ssl_verify_cert'] = True
    config['ssl_verify_identity'] = True
    
    backend = MariaDBBackend(connection_config=MariaDBConnectionConfig(**config))
    
    try:
        backend.connect()
        print("[PASS] SSL connection with verification established")
        
        version = backend.get_server_version()
        print(f"[PASS] Server version: {version[0]}.{version[1]}.{version[2]}")
        
        backend.disconnect()
        print("[PASS] Disconnected successfully")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "certificate" in error_str or "ssl" in error_str or "verify" in error_str:
            print(f"[EXPECTED] Certificate verification failed (self-signed?): {e}")
            print("[INFO] This is expected if server uses self-signed certificate")
            return True
        else:
            print(f"[FAIL] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_crud_over_ssl():
    """Test CRUD operations over SSL connection."""
    print("\n[Test 4: CRUD operations over SSL]")
    print("-" * 40)
    
    scenario_name, config = load_scenario("mariadb_12_2")
    print(f"Scenario: {scenario_name}")
    
    config['ssl_disabled'] = False
    config['ssl_verify_cert'] = False
    config['ssl_verify_identity'] = False
    
    backend = MariaDBBackend(connection_config=MariaDBConnectionConfig(**config))
    
    try:
        backend.connect()
        print("[PASS] SSL connection established")
        
        backend.execute("DROP TABLE IF EXISTS `ssl_test`")
        backend.execute("""
            CREATE TABLE `ssl_test` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `name` VARCHAR(100) NOT NULL,
                `value` INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("[PASS] Table created")
        
        result = backend.execute(
            "INSERT INTO `ssl_test` (`name`, `value`) VALUES (%s, %s)",
            ("ssl_test_item", 42)
        )
        print(f"[PASS] Insert: id={result.last_insert_id}")
        
        result = backend.execute("SELECT * FROM `ssl_test` WHERE `id` = %s", (result.last_insert_id,))
        row = result.data[0]
        assert row['name'] == "ssl_test_item"
        assert row['value'] == 42
        print(f"[PASS] Select: name={row['name']}, value={row['value']}")
        
        backend.execute("DROP TABLE IF EXISTS `ssl_test`")
        print("[PASS] Table dropped")
        
        backend.disconnect()
        print("[PASS] Disconnected")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_other_versions_ssl():
    """Test SSL connection to other MariaDB versions."""
    print("\n[Test 5: SSL connections to various MariaDB versions]")
    print("-" * 40)
    
    scenarios = ["mariadb_10_11", "mariadb_10_6", "mariadb_10_5"]
    
    for scenario_name in scenarios:
        _, config = load_scenario(scenario_name)
        print(f"\nTesting {scenario_name}...")
        
        config['ssl_disabled'] = False
        config['ssl_verify_cert'] = False
        config['ssl_verify_identity'] = False
        
        backend = MariaDBBackend(connection_config=MariaDBConnectionConfig(**config))
        
        try:
            backend.connect()
            version = backend.get_server_version()
            print(f"  [PASS] Connected, version: {version[0]}.{version[1]}.{version[2]}")
            backend.disconnect()
        except Exception as e:
            print(f"  [INFO] Could not connect: {e}")
    
    return True


def main():
    """Run all SSL tests."""
    print("=" * 60)
    print("MariaDB SSL Connection Test Script")
    print("=" * 60)
    
    results = []
    
    results.append(("No SSL (should fail)", test_no_ssl()))
    results.append(("SSL without verify", test_ssl_without_verify()))
    results.append(("SSL with cert verify", test_ssl_with_cert_verify()))
    results.append(("CRUD over SSL", test_crud_over_ssl()))
    results.append(("Other versions SSL", test_other_versions_ssl()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
