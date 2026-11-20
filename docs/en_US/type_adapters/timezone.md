<!-- docs/en_US/type_adapters/timezone.md -->
# Timezone handling

Temporal values cross three layers: Python `datetime` objects, the connector's
session settings, and MariaDB's `DATETIME` / `TIMESTAMP` columns. The backend
helps you keep those layers consistent.

## Choose one convention

- Store **UTC** for instants (events, audit timestamps), and convert to local
  time only in presentation code.
- Use `DATETIME` for wall-clock values where the timezone is not part of the
  data (for example "doors open at 09:00").

`MariaDBConnectionConfig` has a `timezone` field, which feeds the temporal
adaptation path. Set it explicitly when constructing the config; `from_env()`
reads the connection, SSL and charset variables listed in
[Connection configuration](../installation_and_configuration/configuration.md).

## Fractional seconds

MariaDB stores fractional seconds only when the column declares them:

```python
from rhosocial.activerecord.backend.expression.types import TimestampType

created_at: Annotated[datetime, UseSqlType(TimestampType(precision=6))]
```

`DATETIME(6)` / `TIMESTAMP(6)` keep microseconds. Without a declared fraction,
the server rounds, so a value that looks correct in Python can read back one
second off. The `seconds_between` expression counts in `MICROSECOND` and divides
by 1,000,000 for exactly this reason — see
[Datetime expressions](../mariadb_specific_features/datetime_expressions.md).

## TIMESTAMP range

MariaDB `TIMESTAMP` is stored as a Unix timestamp and has a narrower range
(1970-01-01 UTC to 2038-01-19 UTC) than `DATETIME` (1000–9999). Use `DATETIME`
for values outside that window and for wall-clock semantics; use `TIMESTAMP`
when you want server-side timezone conversion.

## DST ambiguity

A local wall-clock time can be ambiguous or nonexistent during a daylight-saving
transition. UTC instants have no such ambiguity. Normalise to UTC before
binding a parameter when the value matters for ordering; MariaDB's
`CONVERT_TZ(...)` can convert inside SQL if the timezone tables are loaded.

## Introspection

Column introspection reports the declared type (including fractional
precision) and default, so you can verify that a deployed schema still matches
the model declaration. See
[Introspection](../mariadb_specific_features/introspection.md).
