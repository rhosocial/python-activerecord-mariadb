#!/bin/bash
# info.sh - MariaDB CLI info command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./info.sh

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
echo "MariaDB CLI - info command examples"
echo "=========================================="

echo ""
echo "--- Basic info (table output) ---"
$PYTHON_CMD info

echo ""
echo "--- Verbose info (protocol families) ---"
$PYTHON_CMD info -v

echo ""
echo "--- Detailed verbose (all details) ---"
$PYTHON_CMD info -vv

echo ""
echo "--- JSON output ---"
$PYTHON_CMD info -o json

echo ""
echo "--- Info with specific MariaDB version ---"
$PYTHON_CMD info --version 5.7.0

echo ""
echo "--- Rich ASCII output ---"
$PYTHON_CMD info --rich-ascii