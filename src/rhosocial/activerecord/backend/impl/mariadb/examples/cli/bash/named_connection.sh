#!/bin/bash
# named_connection.sh - MariaDB CLI named-connection command example
#
# Usage:
#   ./named_connection.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DATABASE="${MYSQL_DATABASE:-test}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"

export MYSQL_HOST MYSQL_PORT MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD

PYTHON_CMD="python -m rhosocial.activerecord.backend.impl.mariadb"

echo "=========================================="
echo "MariaDB CLI - named-connection command examples"
echo "=========================================="

echo ""
echo "--- List all connections in examples module ---"
$PYTHON_CMD named-connection --list rhosocial.activerecord.backend.impl.mariadb.examples.named_connections

echo ""
echo "--- Show specific connection details ---"
$PYTHON_CMD named-connection --show rhosocial.activerecord.backend.impl.mariadb.examples.named_connections.local_dev

echo ""
echo "--- Describe connection config (dry-run) ---"
$PYTHON_CMD named-connection --describe rhosocial.activerecord.backend.impl.mariadb.examples.named_connections.local_dev