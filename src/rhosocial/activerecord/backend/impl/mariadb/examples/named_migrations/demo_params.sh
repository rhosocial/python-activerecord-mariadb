#!/usr/bin/env bash
# ===========================================================================
# demo_params.sh — parameterized migration (--param) for MariaDB
#
# Scenarios:
#   - describe a parameterized migration
#   - apply with custom --param table_name=my_config
#   - dry-run with custom param
#   - rollback with matching --param
#
# Usage:
#   cd python-activerecord-mariadb
#   PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/demo_params.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations"
FQN="${MODULE}.migrations.V003CreateCustomTable"
STORE="./demo_mariadb_params_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.mariadb"

rm -f "$STORE"
echo "=== Parameterized Migration (--param) for MariaDB ==="
echo

echo "[1] Describe V003CreateCustomTable (shows table_name parameter):"
$PYTHON named-migration "$FQN" --describe
echo

echo "[2] Dry-run with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction up --param table_name=my_config --dry-run
echo

echo "[3] Apply UP with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction up --param table_name=my_config --record-store "$STORE"
echo

echo "[4] Rollback with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction down --param table_name=my_config --record-store "$STORE"
echo

echo "[5] Dry-run without --param (uses default 'custom_table'):"
$PYTHON named-migration "$FQN" --host localhost --database test --direction up --dry-run
echo

rm -f "$STORE"
echo "=== Parameterized Migration Demo Complete for MariaDB ==="
