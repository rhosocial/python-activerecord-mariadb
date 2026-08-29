#!/bin/bash
# named_expression.sh - MariaDB CLI named-expression command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./named_expression.sh

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
echo "MariaDB CLI - named-expression command examples"
echo "=========================================="

echo ""
echo "--- List named expressions in examples module ---"
$PYTHON_CMD named-expression --list rhosocial.activerecord.backend.impl.mariadb.examples.named_expressions.order_expressions 2>/dev/null || echo "(No named expressions found)"

echo ""
echo "--- List named connections module for reference ---"
$PYTHON_CMD named-connection --list rhosocial.activerecord.backend.impl.mariadb.examples.named_connections