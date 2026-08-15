#!/bin/bash
# status.sh - MariaDB CLI status command example
#
# Usage:
#   MYSQL_HOST=... MYSQL_PORT=... MYSQL_DATABASE=... MYSQL_USER=... MYSQL_PASSWORD=... ./status.sh

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
echo "MariaDB CLI - status command examples"
echo "=========================================="

echo ""
echo "--- All status ---"
$PYTHON_CMD status all

echo ""
echo "--- Config status ---"
$PYTHON_CMD status config

echo ""
echo "--- Performance status ---"
$PYTHON_CMD status performance

echo ""
echo "--- Databases status ---"
$PYTHON_CMD status databases

echo ""
echo "--- Users status ---"
$PYTHON_CMD status users

echo ""
echo "--- Connections status ---"
$PYTHON_CMD status connections

echo ""
echo "--- Verbose output ---"
$PYTHON_CMD status all -v

echo ""
echo "--- JSON output ---"
$PYTHON_CMD status all -o json

echo ""
echo "--- CSV output ---"
$PYTHON_CMD status config -o csv

echo ""
echo "--- Rich ASCII output ---"
$PYTHON_CMD status config --rich-ascii