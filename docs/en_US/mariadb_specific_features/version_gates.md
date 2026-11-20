<!-- docs/en_US/mariadb_specific_features/version_gates.md -->
# Version gates

MariaDB releases do not all accept the same SQL. The backend keeps one table of
feature floors (`MARIADB_VERSION_BOUNDARIES`) and every gate reads from it, so a
feature's answer is a question about the *connected server*, not about the
client library.

## How a gate resolves

1. `backend.connect()` performs the handshake and learns the server version.
2. `backend.introspect_and_adapt()` makes introspection probes answer for that
   version (the CLI does this at entry; do it yourself before gating).
3. A `supports_*` probe calls `version_at_least(floor)`; a feature newer than
   the floor is assumed available — there is no upper bound that rejects a
   future server.

```python
backend = MariaDBBackend(connection_config=config)
backend.connect()
backend.introspect_and_adapt()

dialect = backend.dialect
print(dialect.get_server_version())
print(dialect.version_at_least((10, 6, 0)))  # JSON_TABLE, EXPLAIN FORMAT=JSON, SKIP LOCKED
```

## Floors at a glance

| Feature | Floor |
|---------|-------|
| Window functions, CTEs, CHECK constraints | 10.2 (CHECK: 10.2.1) |
| JSON functions / JSON arrows | 10.2.3 / 10.2.7 |
| INTERSECT / EXCEPT, sequences, system versioning | 10.3 |
| INSTEAD OF triggers | 10.4 |
| `RETURNING` (INSERT/DELETE/REPLACE), rename-if-exists | 10.5 |
| `FORMAT=JSON`, `JSON_TABLE`, `SKIP LOCKED` | 10.6 |
| UUID data type | 10.7 |
| `EXCHANGE PARTITION` validation | 11.4 |
| Native XMLTYPE, `IS JSON` predicate | 12.3 |
| `RETURNING` for UPDATE | 13.0 |

Two related capabilities own *different* floors: `FOR UPDATE NOWAIT` (10.3) and
`FOR UPDATE SKIP LOCKED` (10.6). They are separate probes because the servers
between those versions accept one spelling and reject the other.

## Consequences for generated SQL

- A renderer only emits syntax whose gate is `True`; otherwise it falls back to
  an equivalent (for example JSON → `LONGTEXT`) or raises
  `UnsupportedFeatureError`.
- A `True` answer means "the statement is expected to be accepted", not "the
  feature is free". Check the
  [introspection](../mariadb_specific_features/introspection.md) page for the
  version-dependent answers of the introspection probes.
- 12.3 is the recommended baseline for new deployments; 13.1 is a release
  candidate and is not recommended for production.

The full policy and the CI version matrix are in
[Supported versions](../introduction/supported_versions.md).
