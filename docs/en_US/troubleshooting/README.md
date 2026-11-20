<!-- docs/en_US/troubleshooting/README.md -->
# Troubleshooting

## Chapters

- [Connection errors](connection.md) — handshake, TLS and authentication failures
- [Performance](performance.md) — slow statements, locking and plan regressions

## General approach

1. Confirm the server version and that the feature you are using is enabled for
   it ([Version gates](../mariadb_specific_features/version_gates.md)).
2. Preview the generated SQL with `.to_sql()` before executing it.
3. Check what the server actually declares with
   [Introspection](../mariadb_specific_features/introspection.md) rather than
   what the model thinks it declared.
4. Read the plan with [EXPLAIN](../mariadb_specific_features/explain.md).

For modeling and query errors that are not MariaDB-specific, consult the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
