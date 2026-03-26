# scripts/test_crud.py
"""Simple CRUD test script for MariaDB backend.

This script tests basic Create, Read, Update, Delete operations
to verify the MariaDB backend implementation works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import yaml
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def load_scenario(scenario_name: str = "mariadb_10_11"):
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


def create_test_table(backend):
    """Create a simple test table."""
    backend.execute("DROP TABLE IF EXISTS `test_crud`")
    backend.execute("""
        CREATE TABLE `test_crud` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `name` VARCHAR(100) NOT NULL,
            `value` INT DEFAULT 0,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("[PASS] Table created successfully")


def test_insert(backend):
    """Test INSERT operation."""
    result = backend.execute(
        "INSERT INTO `test_crud` (`name`, `value`) VALUES (%s, %s)",
        ("test_item_1", 100)
    )
    assert result is not None, "Insert result should not be None"
    assert result.last_insert_id is not None, "Should have last_insert_id"
    assert result.last_insert_id > 0, "last_insert_id should be positive"
    print(f"[PASS] Insert: id={result.last_insert_id}, affected={result.affected_rows}")
    return result.last_insert_id


def test_select(backend, record_id):
    """Test SELECT operation."""
    result = backend.execute(
        "SELECT * FROM `test_crud` WHERE `id` = %s",
        (record_id,)
    )
    assert result is not None, "Select result should not be None"
    assert result.data is not None, "Should have data"
    assert len(result.data) == 1, f"Should have 1 row, got {len(result.data)}"
    
    row = result.data[0]
    assert row['id'] == record_id, f"ID mismatch: {row['id']} != {record_id}"
    assert row['name'] == "test_item_1", f"Name mismatch: {row['name']}"
    assert row['value'] == 100, f"Value mismatch: {row['value']}"
    print(f"[PASS] Select: id={row['id']}, name={row['name']}, value={row['value']}")
    return row


def test_update(backend, record_id):
    """Test UPDATE operation."""
    result = backend.execute(
        "UPDATE `test_crud` SET `name` = %s, `value` = %s WHERE `id` = %s",
        ("test_item_updated", 200, record_id)
    )
    assert result is not None, "Update result should not be None"
    assert result.affected_rows == 1, f"Should affect 1 row, got {result.affected_rows}"
    print(f"[PASS] Update: affected_rows={result.affected_rows}")
    
    result = backend.execute(
        "SELECT * FROM `test_crud` WHERE `id` = %s",
        (record_id,)
    )
    row = result.data[0]
    assert row['name'] == "test_item_updated", f"Updated name mismatch: {row['name']}"
    assert row['value'] == 200, f"Updated value mismatch: {row['value']}"
    print(f"[PASS] Update verified: name={row['name']}, value={row['value']}")


def test_delete(backend, record_id):
    """Test DELETE operation."""
    result = backend.execute(
        "DELETE FROM `test_crud` WHERE `id` = %s",
        (record_id,)
    )
    assert result is not None, "Delete result should not be None"
    assert result.affected_rows == 1, f"Should affect 1 row, got {result.affected_rows}"
    print(f"[PASS] Delete: affected_rows={result.affected_rows}")
    
    result = backend.execute(
        "SELECT * FROM `test_crud` WHERE `id` = %s",
        (record_id,)
    )
    assert len(result.data) == 0, "Row should be deleted"
    print("[PASS] Delete verified: row no longer exists")


def test_batch_insert(backend):
    """Test batch INSERT operation."""
    params_list = [
        ("batch_1", 10),
        ("batch_2", 20),
        ("batch_3", 30),
    ]
    result = backend.execute_many(
        "INSERT INTO `test_crud` (`name`, `value`) VALUES (%s, %s)",
        params_list
    )
    assert result is not None, "Batch insert result should not be None"
    assert result.affected_rows == 3, f"Should affect 3 rows, got {result.affected_rows}"
    print(f"[PASS] Batch insert: affected_rows={result.affected_rows}")
    
    result = backend.execute("SELECT COUNT(*) as cnt FROM `test_crud`")
    count = result.data[0]['cnt']
    assert count == 3, f"Should have 3 rows, got {count}"
    print(f"[PASS] Batch insert verified: {count} rows in table")


def test_dialect(backend):
    """Test dialect functionality."""
    dialect = backend.dialect
    
    assert dialect.name.lower() == "mariadb", f"Dialect name should be 'mariadb', got '{dialect.name}'"
    print(f"[PASS] Dialect name: {dialect.name}")
    
    placeholder = dialect.get_parameter_placeholder(0)
    assert placeholder == "%s", f"Placeholder should be '%%s', got '{placeholder}'"
    print(f"[PASS] Parameter placeholder: '{placeholder}'")
    
    identifier = dialect.format_identifier("test_table")
    assert identifier == "`test_table`", f"Identifier should be '`test_table`', got '{identifier}'"
    print(f"[PASS] Format identifier: {identifier}")
    
    version = dialect.get_server_version()
    print(f"[PASS] Server version from dialect: {version}")


def test_version_detection(backend):
    """Test server version detection."""
    version = backend.get_server_version()
    assert version is not None, "Version should not be None"
    assert len(version) == 3, f"Version should be tuple of 3, got {len(version)}"
    assert version[0] >= 10, f"MariaDB major version should be >= 10, got {version[0]}"
    print(f"[PASS] Server version: {version[0]}.{version[1]}.{version[2]}")


def test_transaction(backend):
    """Test transaction functionality."""
    backend.execute("DELETE FROM `test_crud`")
    
    tm = backend.transaction_manager
    
    tm.begin()
    print("[PASS] Transaction begin")
    
    backend.execute("INSERT INTO `test_crud` (`name`, `value`) VALUES (%s, %s)", ("tx_test", 999))
    
    result = backend.execute("SELECT COUNT(*) as cnt FROM `test_crud`")
    assert result.data[0]['cnt'] == 1, "Should have 1 row inside transaction"
    print("[PASS] Row visible inside transaction")
    
    tm.rollback()
    print("[PASS] Transaction rollback")
    
    result = backend.execute("SELECT COUNT(*) as cnt FROM `test_crud`")
    assert result.data[0]['cnt'] == 0, "Should have 0 rows after rollback"
    print("[PASS] Rollback verified: no rows after rollback")
    
    tm.begin()
    backend.execute("INSERT INTO `test_crud` (`name`, `value`) VALUES (%s, %s)", ("tx_commit", 888))
    tm.commit()
    print("[PASS] Transaction commit")
    
    result = backend.execute("SELECT COUNT(*) as cnt FROM `test_crud`")
    assert result.data[0]['cnt'] == 1, "Should have 1 row after commit"
    print("[PASS] Commit verified: 1 row after commit")


def cleanup(backend):
    """Clean up test table."""
    try:
        backend.execute("DROP TABLE IF EXISTS `test_crud`")
        print("[PASS] Cleanup: table dropped")
    except Exception as e:
        print(f"[WARN] Cleanup error: {e}")


def main():
    """Run all CRUD tests."""
    print("=" * 60)
    print("MariaDB Backend CRUD Test Script")
    print("=" * 60)
    
    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "mariadb_10_11"
    scenario_name, scenario_config = load_scenario(scenario_name)
    print(f"\nUsing scenario: {scenario_name}")
    print(f"Config: host={scenario_config.get('host')}, port={scenario_config.get('port')}")
    
    config = MariaDBConnectionConfig(**scenario_config)
    backend = MariaDBBackend(connection_config=config)
    
    try:
        print("\n[Phase 1: Connection]")
        backend.connect()
        print("[PASS] Connected successfully")
        
        print("\n[Phase 2: Version Detection]")
        test_version_detection(backend)
        
        print("\n[Phase 3: Dialect Tests]")
        test_dialect(backend)
        
        print("\n[Phase 4: Table Creation]")
        create_test_table(backend)
        
        print("\n[Phase 5: CRUD Operations]")
        record_id = test_insert(backend)
        test_select(backend, record_id)
        test_update(backend, record_id)
        test_delete(backend, record_id)
        
        print("\n[Phase 6: Batch Operations]")
        test_batch_insert(backend)
        
        print("\n[Phase 7: Transaction Tests]")
        test_transaction(backend)
        
        print("\n[Phase 8: Cleanup]")
        cleanup(backend)
        
        print("\n" + "=" * 60)
        print("All tests PASSED!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        backend.disconnect()
        print("\n[PASS] Disconnected")


if __name__ == "__main__":
    sys.exit(main())
