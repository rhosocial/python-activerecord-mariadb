#!/bin/bash
# introspect.sh - MariaDB CLI introspect command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./introspect.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DATABASE="${MYSQL_DATABASE:-test}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"

export MYSQL_HOST MYSQL_PORT MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD

PYTHON_CMD="python -m rhosocial.activerecord.backend.impl.mariadb"

TEST_TABLE_USERS="cli_test_users"
TEST_TABLE_ORDERS="cli_test_orders"

cleanup() {
    echo "Cleaning up..."
    $PYTHON_CMD query "DROP TABLE IF EXISTS $TEST_TABLE_ORDERS" 2>/dev/null || true
    $PYTHON_CMD query "DROP TABLE IF EXISTS $TEST_TABLE_USERS" 2>/dev/null || true
}

setup() {
    echo "Setting up test data..."
    $PYTHON_CMD query "CREATE TABLE IF NOT EXISTS $TEST_TABLE_USERS (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100)
    )"
    $PYTHON_CMD query "INSERT INTO $TEST_TABLE_USERS (name, email) VALUES
        ('Alice', 'alice@example.com'), ('Bob', 'bob@example.com')"
    $PYTHON_CMD query "CREATE TABLE IF NOT EXISTS $TEST_TABLE_ORDERS (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT,
        amount DECIMAL(10,2)
    )"
    $PYTHON_CMD query "INSERT INTO $TEST_TABLE_ORDERS (user_id, amount) VALUES (1, 100.00)"
}

trap cleanup EXIT

echo "=========================================="
echo "MariaDB CLI - introspect command examples"
echo "=========================================="

setup

echo ""
echo "--- List all tables ---"
$PYTHON_CMD introspect tables

echo ""
echo "--- List all views ---"
$PYTHON_CMD introspect views

echo ""
echo "--- Get table details ---"
$PYTHON_CMD introspect table $TEST_TABLE_USERS

echo ""
echo "--- Get column details ---"
$PYTHON_CMD introspect columns $TEST_TABLE_USERS

echo ""
echo "--- Get indexes ---"
$PYTHON_CMD introspect indexes $TEST_TABLE_USERS

echo ""
echo "--- Get foreign keys ---"
$PYTHON_CMD introspect foreign-keys $TEST_TABLE_ORDERS

echo ""
echo "--- Get database info ---"
$PYTHON_CMD introspect database

echo ""
echo "--- JSON output ---"
$PYTHON_CMD introspect tables -o json

echo ""
echo "--- CSV output ---"
$PYTHON_CMD introspect tables -o csv

echo ""
echo "--- TSV output ---"
$PYTHON_CMD introspect tables -o tsv

echo ""
echo "--- Include system tables ---"
$PYTHON_CMD introspect tables --include-system | head -10