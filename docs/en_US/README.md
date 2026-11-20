<!-- docs/en_US/README.md -->
# rhosocial-activerecord MariaDB Backend Documentation

> 🤖 **AI Learning Assistant**: Key concepts in this documentation are marked with
> 💡 AI Prompt markers. When you encounter a concept you don't understand, ask the
> AI assistant directly.
>
> **Example:** "How does the MariaDB backend gate a feature on the connected
> server version?"
>
> 📖 **See also**: the
> [GitBook-style summary](SUMMARY.md) for the flat chapter list.

This is the MariaDB backend for
[rhosocial-activerecord](https://github.com/rhosocial/python-activerecord). It
uses the `mariadb` connector and brings the ActiveRecord pattern to MariaDB,
including MariaDB-native features such as system-versioned tables, sequences,
`RETURNING`, full-text search, JSON operators, partitioning, and the engine's own
type set. Both `MariaDBBackend` and `AsyncMariaDBBackend` are shipped.

This manual covers **this backend only**. Modeling, querying, relationships, and
the generic expression layer are documented in the
[core library documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).

## Table of Contents

1. **[Introduction](introduction/README.md)**
     * **[Overview](introduction/README.md)**: what this backend is and what it adds
     * **[Relationship with the core library](introduction/relationship.md)**: where the backend ends and core begins
     * **[Supported versions](introduction/supported_versions.md)**: MariaDB 10.2–13.1-rc, Python 3.8+, version policy

2. **[Installation & Configuration](installation_and_configuration/README.md)**
     * **[Installation](installation_and_configuration/installation.md)**: pip install, connector and Python requirements
     * **[Connection configuration](installation_and_configuration/configuration.md)**: `MariaDBConnectionConfig`, `configure()`, `from_env()`
     * **[SSL/TLS](installation_and_configuration/ssl.md)**: TLS flags and certificate material
     * **[Connection management](installation_and_configuration/pool.md)**: connect-on-use and reconnect behaviour
     * **[Character set & collation](installation_and_configuration/charset.md)**: `utf8mb4` and the `utf8` alias

3. **[MariaDB-Specific Features](mariadb_specific_features/README.md)**
     * **[Field types](mariadb_specific_features/field_types.md)**: MariaDB native and extended column types
     * **[Dialect](mariadb_specific_features/dialect.md)**: quoting, literals and MariaDB SQL spelling
     * **[Version gates](mariadb_specific_features/version_gates.md)**: how features resolve against the connected server
     * **[Storage engines](mariadb_specific_features/storage_engine.md)**: InnoDB and other engines
     * **[Indexing](mariadb_specific_features/indexing.md)**: index design and DDL
     * **[Introspection](mariadb_specific_features/introspection.md)**: what the backend asks the server and where the answers come from
     * **[Partitioning](mariadb_specific_features/partition.md)**: RANGE/LIST/HASH/KEY, maintenance and subpartitioning
     * **[Datetime expressions](mariadb_specific_features/datetime_expressions.md)**: `seconds_between` and fractional precision
     * **[EXPLAIN](mariadb_specific_features/explain.md)**: query plans and `ANALYZE FORMAT=JSON`

4. **[DDL Operations](ddl/README.md)**
     * **[DDL overview](ddl/README.md)**: model-driven DDL and statement-level DDL
     * **[Example: create table](../examples/chapter_04_ddl/ddl.py)**: runnable DDL script

5. **[Transaction Support](transaction_support/README.md)**
     * **[Isolation levels](transaction_support/isolation_level.md)**: transaction modes and isolation
     * **[Savepoints](transaction_support/savepoint.md)**: nested units of work
     * **[Deadlocks & retry](transaction_support/deadlock.md)**: failure handling

6. **[Type Adapters](type_adapters/README.md)**
     * **[Type mapping](type_adapters/mapping.md)**: Python ↔ MariaDB conversions
     * **[Custom adapters](type_adapters/custom.md)**: extending conversion
     * **[Timezone handling](type_adapters/timezone.md)**: temporal values

7. **[Testing](testing/README.md)**
     * **[Test configuration](testing/configuration.md)**: environment and scenarios
     * **[Local testing](testing/local.md)**: running against a local server

8. **[Troubleshooting](troubleshooting/README.md)**
     * **[Connection errors](troubleshooting/connection.md)**: diagnosis
     * **[Performance](troubleshooting/performance.md)**: common bottlenecks

9. **[Examples](../examples/README.md)**
     * **[Connection](../examples/chapter_06_connection/README.md)**
     * **[DDL](../examples/chapter_04_ddl/README.md)**
     * **[Introspection](../examples/chapter_05_introspection/README.md)**

---

> 📖 **Core library documentation**: for the complete ActiveRecord framework, see
> [rhosocial-activerecord documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
