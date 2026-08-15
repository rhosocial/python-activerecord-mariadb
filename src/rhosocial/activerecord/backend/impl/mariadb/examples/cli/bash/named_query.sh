#!/bin/bash
# named_query.sh - MariaDB CLI named-query command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./named_query.sh

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
echo "MariaDB CLI - named-query command examples"
echo "=========================================="

echo ""
echo "--- List named queries in examples module ---"
$PYTHON_CMD named-query --list rhosocial.activerecord.backend.impl.mariadb.examples.named_queries 2>/dev/null || echo "(No named queries found)"

echo ""
echo "--- List named connections module for reference ---"
$PYTHON_CMD named-connection --list rhosocial.activerecord.backend.impl.mariadb.examples.named_connections