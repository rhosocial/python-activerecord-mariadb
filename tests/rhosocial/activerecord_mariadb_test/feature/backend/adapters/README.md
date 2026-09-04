# adapters tests

Offline round-trip coverage for the MariaDB type adapters (to_database / from_database with None semantics), the MariaDBDateAdapter isinstance-ordering regression and ENUM adapter tests (unit + real-database integration). Backend-integrated column mapping lives in `../dml/`.

## Key files

- `test_adapters.py` — offline adapter round trips
- `test_date_adapter.py` — date/datetime adapter regression
- `test_enum_adapter.py` — ENUM adapter unit tests
- `test_enum_adapter_backend.py` — ENUM adapter integration (sync/async)
