#!/bin/bash
# named_procedure.sh - MariaDB CLI named-procedure command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./named_procedure.sh

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
echo "MariaDB CLI - named-procedure command examples"
echo "=========================================="

echo ""
echo "--- List named procedures in examples module ---"
$PYTHON_CMD named-procedure --list rhosocial.activerecord.backend.impl.mariadb.examples.named_procedures 2>/dev/null || echo "(No named procedures found)"

echo ""
echo "--- List named connections module for reference ---"
$PYTHON_CMD named-connection --list rhosocial.activerecord.backend.impl.mariadb.examples.named_connections