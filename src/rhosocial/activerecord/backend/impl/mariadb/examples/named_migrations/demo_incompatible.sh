#!/usr/bin/env bash
# ===========================================================================
# demo_incompatible.sh — dialect incompatibility via dry-run for MariaDB
#
# Scenarios:
#   - compatible migration dry-run succeeds
#   - incompatible expression (invalid reference) caught as MigrationDialectError
#
# Usage:
#   cd python-activerecord-mariadb
#   PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/demo_incompatible.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations"
FQN="${MODULE}.migrations.V001CreateUsers"
STORE="./demo_mariadb_ic_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.mariadb"

rm -f "$STORE"
echo "=== Dialect Incompatibility Detection for MariaDB ==="
echo

echo "[1] Compatible migration dry-run (should succeed):"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction up --dry-run
echo

echo "[2] Demonstration:"
echo "    The named migration system catches dialect incompatibilities at dry-run"
echo "    time via to_sql() on each expression. If an expression uses a feature"
echo "    not supported by the connected MariaDB version, UnsupportedFeatureError"
echo "    is caught and wrapped as MigrationDialectError."
echo
echo "    Incompatible migrations produce output like:"
echo "      Dialect Error: 'mariadb' dialect does not support PARTITION BY RANGE"
echo

echo "[3] Compatible apply UP (succeeds):"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction up --record-store "$STORE" 2>&1 || true
echo

echo "[4] Rollback DOWN:"
$PYTHON named-migration "$FQN" --host localhost --database test \
    --direction down --record-store "$STORE"
echo

rm -f "$STORE"
echo "=== Dialect Incompatibility Demo Complete for MariaDB ==="
