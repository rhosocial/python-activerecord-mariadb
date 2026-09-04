# transactions tests

Real-server transaction behavior: the actual effects of isolation levels, transaction access modes and combinations, nested transactions, backend-level transaction handling for sync and async backends, and offline auto-commit handler tests.

## Key files

- `test_autocommit_backend.py` — auto-commit handlers (offline)
- `test_isolation_effect.py` — isolation level / mode effects and nesting (sync)
- `test_isolation_effect_async.py` — isolation level / mode effects and nesting (async)
- `test_transaction_backend.py` — begin/commit/rollback integration (sync)
- `test_transaction_backend_async.py` — begin/commit/rollback integration (async)
