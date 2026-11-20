<!-- docs/en_US/introduction/README.md -->
# Introduction

The MariaDB backend is a separate distribution that plugs into
`rhosocial-activerecord`. It cannot be used standalone: models, field proxies,
query builders, events and the expression system come from the core library,
and this package supplies the dialect, driver bridge, introspector, type
adapters and MariaDB-only expression nodes.

## What this backend adds

- **Native MariaDB SQL** — `AUTO_INCREMENT`, system versioning, sequences,
  `RETURNING`, full-text predicates, JSON operators, partitioning, and
  engine/charset table options are rendered by this backend's dialect.
- **Version-aware SQL** — the dialect reads the connected server version and
  emits only syntax that server accepts (see
  [Version gates](../mariadb_specific_features/version_gates.md)).
- **True sync/async parity** — `MariaDBBackend` and `AsyncMariaDBBackend` are
  native implementations with the same method names; the async variant only
  adds `await`.
- **Declarative models** — annotate fields with `UseSqlType(...)` and let core
  build the DDL. Hand-written `CREATE TABLE` expressions remain available for
  backend-specific options.
- **Three introspection layers** — schema declarations, operational facts and
  row-level data profiles (see
  [Introspection](../mariadb_specific_features/introspection.md)).

## Architecture at a glance

```
Your code
   ↓  models, field proxies, query builders
ActiveRecord core
   ↓  generic expressions → statements
MariaDB dialect
   ↓  version-aware rendering, quoting, adapters
mariadb connector
   ↓
MariaDB server
```

Query structure stays decoupled from SQL generation: nothing is rendered until
an explicit `.to_sql()` call, so every statement can be previewed before it
runs.

## Chapters

- [Relationship with the core library](relationship.md)
- [Supported versions](supported_versions.md)

Next: [Installation](../installation_and_configuration/installation.md).
