#!/usr/bin/env bash
# ===========================================================================
# demo_all.sh — batch migration (--all) for MariaDB
#
# Scenarios:
#   - --all runs all pending migrations in dependency order
#   - --all --dry-run preview without changes
#   - --all --direction down rolls back everything
#
# Usage:
#   cd python-activerecord-mariadb
#   DEMO_VENV_PYTHON=.venv3.13/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/demo_all.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations"
STORE="./demo_mariadb_all_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.mariadb"

rm -f "$STORE"
echo "=== Batch Migration (--all) for MariaDB ==="
echo

echo "[1] --all without --record-store (should error):"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test 2>&1 || true
echo

echo "[2] --all --dry-run (preview SQL, no changes):"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test --dry-run --record-store "$STORE"
echo

echo "[3] --all apply all pending migrations:"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test --record-store "$STORE"
echo

echo "[4] Re-run --all (all applied, should be no-op):"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test --record-store "$STORE" 2>&1 || true
echo

echo "[5] --all --single-transaction (rollback in one transaction):"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test \
    --direction down --record-store "$STORE" --single-transaction
echo

echo "[6] --all --single-transaction (re-apply UP):"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test \
    --direction up --record-store "$STORE" --single-transaction
echo

echo "[7] --all --direction down rollback everything:"
$PYTHON named-migration "${MODULE}.migrations" --all --host localhost --database test \
    --direction down --record-store "$STORE"
echo

echo "[8] Record store final state:"
cat "$STORE"
echo

rm -f "$STORE"
echo "=== Batch Migration (--all) Complete for MariaDB ==="
