# dml tests

MariaDB DML coverage: CRUD and column mapping against the backend (sync/async), INSERT IGNORE, ON CONFLICT mapped to ON DUPLICATE KEY UPDATE, LOAD DATA INFILE, REPLACE INTO and integration tests for the dialect security fixes.

## Key files

- `test_column_mapping_backend.py` — backend column mapping (sync)
- `test_column_mapping_backend_async.py` — backend column mapping (async)
- `test_crud_backend.py` — CRUD integration (sync)
- `test_crud_backend_async.py` — CRUD integration (async)
- `test_dialect_security_integration.py` — security fixes executed on the server
- `test_insert_ignore.py` — INSERT IGNORE (sync/async)
- `test_insert_on_conflict_clauses.py` — ON DUPLICATE KEY UPDATE capabilities/rendering
- `test_load_data.py` — LOAD DATA INFILE
- `test_replace_into.py` — REPLACE INTO
