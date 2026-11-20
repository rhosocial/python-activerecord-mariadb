<!-- docs/en_US/introduction/supported_versions.md -->
# Supported versions

## MariaDB

The backend is tested in CI against:

**10.2, 10.3, 10.4, 10.5, 10.6, 10.11, 11.4, 11.7, 11.8, 12.0, 12.2, 12.3,
13.0 and 13.1-rc.**

There is no upper bound: a newer server is not rejected. Feature gates resolve
to *enabled* when the server is newer than the version that introduced the
feature, so new syntax is assumed to be available. If that assumption is ever
wrong, the server rejects the statement rather than the backend guessing.
Features removed in later releases report themselves unsupported per feature.

**12.3 is the recommended baseline** — an LTS line maintained to June 2029.
13.1 is a release candidate and is not recommended for production.

## Python and driver

- Python **3.8+** (`requires-python = ">=3.8"`).
- `mariadb` connector **≥ 2.0.0rc2** — the same connector family is used by both
  `MariaDBBackend` and `AsyncMariaDBBackend`.
- Core library **`rhosocial-activerecord >= 1.0.0.dev30, < 2.0.0`**.

## Feature floors

The dialect keeps one table of version boundaries (`MARIADB_VERSION_BOUNDARIES`)
and every gate reads from it:

| Feature | Floor |
|---------|-------|
| Window functions, CTEs | 10.2 |
| JSON functions / JSON arrows | 10.2.3 / 10.2.7 |
| CHECK constraints | 10.2.1 |
| INTERSECT / EXCEPT, sequences, system versioning | 10.3 |
| INSTEAD OF triggers | 10.4 |
| `RETURNING` (INSERT/DELETE/REPLACE) | 10.5 |
| `FORMAT=JSON` for EXPLAIN, `JSON_TABLE`, `SKIP LOCKED` | 10.6 |
| UUID data type | 10.7 |
| `EXCHANGE PARTITION` validation | 11.4 |
| Native XMLTYPE, `IS JSON` predicate | 12.3 |
| `RETURNING` for UPDATE | 13.0 |

Two gates deliberately carry *separate* floors: `FOR UPDATE NOWAIT` (10.3) and
`FOR UPDATE SKIP LOCKED` (10.6) are not accepted by the same server range, so a
shared probe would have admitted statements the server rejects.

See [Version gates](../mariadb_specific_features/version_gates.md) for how to
ask a probe at runtime.
