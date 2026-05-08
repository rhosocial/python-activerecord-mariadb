#!/bin/bash
# query.sh - MariaDB CLI query command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./query.sh

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
        status VARCHAR(20) DEFAULT 'active'
    )"
    $PYTHON_CMD query "INSERT INTO $TEST_TABLE_USERS (name, status) VALUES
        ('Alice', 'active'), ('Bob', 'inactive'), ('Charlie', 'active')"
    $PYTHON_CMD query "CREATE TABLE IF NOT EXISTS $TEST_TABLE_ORDERS (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT,
        amount DECIMAL(10,2)
    )"
    $PYTHON_CMD query "INSERT INTO $TEST_TABLE_ORDERS (user_id, amount) VALUES
        (1, 100.00), (1, 200.00), (2, 150.00)"
}

trap cleanup EXIT

echo "=========================================="
echo "MariaDB CLI - query command examples"
echo "=========================================="

setup

echo ""
echo "--- Simple SELECT ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS"

echo ""
echo "--- SELECT with WHERE ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS WHERE status = 'active'"

echo ""
echo "--- JOIN query ---"
$PYTHON_CMD query "SELECT u.name, o.amount FROM $TEST_TABLE_USERS u JOIN $TEST_TABLE_ORDERS o ON u.id = o.user_id"

echo ""
echo "--- Aggregate query ---"
$PYTHON_CMD query "SELECT user_id, SUM(amount) as total FROM $TEST_TABLE_ORDERS GROUP BY user_id"

echo ""
echo "--- JSON output ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS" -o json

echo ""
echo "--- CSV output ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS LIMIT 2" -o csv

echo ""
echo "--- TSV output ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS LIMIT 2" -o tsv

echo ""
echo "--- With log level ---"
$PYTHON_CMD query --log-level DEBUG "SELECT 1" 2>&1 | head -5

echo ""
echo "--- Query from file ---"
echo "SELECT * FROM $TEST_TABLE_USERS WHERE id > 0" > /tmp/test_query.sql
$PYTHON_CMD query -f /tmp/test_query.sql
rm -f /tmp/test_query.sql

echo ""
echo "--- Rich ASCII output ---"
$PYTHON_CMD query "SELECT * FROM $TEST_TABLE_USERS LIMIT 2" --rich-ascii