# backend tests

MariaDBBackend process-level behavior: connection resilience (timeout, kill, ping/reconnect, interruption recovery) and async error-class handling. Explain moved to `../query/`, CRUD and column mapping to `../dml/`, auto-commit to `../transactions/`.

## Key files

- `test_backend_error_handling_async.py` — async error classes
- `test_connection_resilience.py` — connection loss / recovery matrix
