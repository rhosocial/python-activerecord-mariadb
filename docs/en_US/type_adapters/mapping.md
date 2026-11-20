<!-- docs/en_US/type_adapters/mapping.md -->
# Type mapping

The table below describes the conversions this backend performs. "Target type"
is the Python type the column is adapted to, which the model declaration or
`UseSqlType(...)` fixes.

| Python | MariaDB column | Adapter behaviour |
|--------|----------------|-------------------|
| `int` | `TINYINT` / `INT` / `BIGINT` / `SERIAL` | Passed through; `SERIAL` yields an unsigned auto-increment key |
| `Decimal` | `DECIMAL(p, s)` | Kept as `Decimal` — never routed through `float` |
| `float` | `FLOAT` / `DOUBLE` | Passed through (avoid for money) |
| `str` | `VARCHAR` / `TEXT` / `CHAR` | Passed through with connection charset conversion |
| `bytes` | `BLOB` / `VARBINARY` | `MariaDBBlobAdapter` passes bytes through |
| `dict`, `list` | `JSON` / `LONGTEXT` | `MariaDBJSONAdapter` does `json.dumps` / `json.loads` |
| `uuid.UUID` | `UUID` / `CHAR(36)` / `BINARY(16)` | `MariaDBUUIDAdapter` converts to text or bytes based on target type |
| `datetime.datetime` | `DATETIME(fsp)` / `TIMESTAMP(fsp)` | Timezone-aware handling; fractional seconds preserved up to `fsp` |
| `datetime.date` | `DATE` | Passed through |
| `datetime.timedelta` | `TIME` | Passed through |
| `bool` | `TINYINT(1)` / `BOOLEAN` | Converted to/from 0/1 by the connector |
| `enum.Enum` | `ENUM` / `SET` | Name or value per the ENUM/SET expression family |
| geometry objects | `GEOMETRY`, `POINT`, … | `GeometryAdapterBase` → WKB, with SRID exposed by introspection |
| `BitString` | `BIT(M)` | `BitStringAdapterBase` |
| `Range`, `Multirange` | MariaDB range types | `RangeAdapterBase` |
| `Vector` | vector column | `VectorAdapterBase` |

## JSON details

`MariaDBJSONAdapter` stores JSON as `LONGTEXT` using `json.dumps(...,
ensure_ascii=False)` and reads it back with `json.loads`. It accepts
`default=` and `object_hook=` arguments so neutral-type codecs can be plugged
in without changing the default behaviour. From MariaDB 10.4.3 a `JSON` column
also carries an automatic `CHECK (json_valid(...))`, so invalid text is
rejected by the server.

`NULL` stays `NULL` in every adapter: `to_database` and `from_database` return
`None` for a `None` input.

## Exactness rules

- Money and any value where rounding matters must use `Decimal` with
  `DECIMAL(p, s)` — never `float`.
- Elapsed time with sub-second precision uses `TIMESTAMPDIFF(MICROSECOND, ...)`
  divided by 1,000,000; see
  [Datetime expressions](../mariadb_specific_features/datetime_expressions.md).
- A narrower-than-needed numeric column can truncate values silently, so size
  integer columns for their full range.
