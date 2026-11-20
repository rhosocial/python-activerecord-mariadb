# query/relation tests (MariaDB bridge)

MariaDB bridge for the shared `feature/query/relation` testsuite topic. This
directory mirrors the testsuite source tree, where the old `feature/relation`
topic was moved under `feature/query/relation`.

- `conftest.py` -> star-imports `testsuite.feature.query.relation.conftest`.
- `core/` -> backend-local relation unit tests (no database required).
- `ordering/` -> bridge to `testsuite.feature.query.relation.ordering`.
- `legacy/` -> the old `query/relations` real-database `with_()` integration
  tests (`test_with_integration.py`) plus a self-contained L2 conftest.

See [feature tests](../README.md) and [tests/README.md](../../../../README.md).
