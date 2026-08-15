#!/usr/bin/env bash
# ===========================================================================
# demo_async.sh — async migration execution (--async) for MariaDB
#
# Scenarios:
#   - apply UP with --async
#   - dry-run with --async
#   - rollback DOWN with --async
#
# Requires: mariadb>=2.0.0rc2 (native async via mariadb.asyncConnect)
#
# Usage:
#   cd python-activerecord-mariadb
#   PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/mariadb/examples/named_migrations/demo_async.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.mariadb.examples.named_migrations"
# AsyncNamedMigration subclass — required by AsyncMigrationRunner (selected via --async).
FQN="${MODULE}.async_migrations.V001CreateUsersAsync"
STORE="./demo_mariadb_async_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.mariadb"

# Connection info — safe defaults (localhost / empty password); override via env.
MARIADB_HOST="${MARIADB_HOST:-localhost}"
MARIADB_PORT="${MARIADB_PORT:-3306}"
MARIADB_DATABASE="${MARIADB_DATABASE:-test}"
MARIADB_USER="${MARIADB_USER:-root}"
MARIADB_PASSWORD="${MARIADB_PASSWORD:-}"
CONN_ARGS="--host $MARIADB_HOST --port $MARIADB_PORT --database $MARIADB_DATABASE --user $MARIADB_USER --password $MARIADB_PASSWORD"

rm -f "$STORE"
echo "=== Async Migration (--async) for MariaDB ==="
echo

echo "[1] Async dry-run (preview SQL, no changes):"
$PYTHON named-migration "$FQN" $CONN_ARGS \
    --direction up --dry-run --async
echo

echo "[2] Async apply UP:"
$PYTHON named-migration "$FQN" $CONN_ARGS \
    --direction up --async --record-store "$STORE"
echo

echo "[3] Async rollback DOWN:"
$PYTHON named-migration "$FQN" $CONN_ARGS \
    --direction down --async --record-store "$STORE"
echo

rm -f "$STORE"
echo "=== Async Migration Demo Complete for MariaDB ==="
