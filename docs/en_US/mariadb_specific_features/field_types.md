<!-- docs/en_US/mariadb_specific_features/field_types.md -->
# MariaDB field types

Model fields declare Python types; `UseSqlType(...)` pins the exact SQL type the
backend should use. The backend renders that type with MariaDB's spelling and
adapts values on the way in and out.

## Declaring a native type

```python
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType, DecimalType
from rhosocial.activerecord.model import ActiveRecord


class Invoice(ActiveRecord):
    code: Annotated[str, UseSqlType(VarCharType(length=32))]
    amount: Annotated[object, UseSqlType(DecimalType(precision=12, scale=2))]

    c: ClassVar[FieldProxy] = FieldProxy()
```

`DecimalType(precision, scale)` maps to `DECIMAL(12, 2)` and keeps money out of
`float`. `VarCharType(length)` maps to `VARCHAR(n)` with MariaDB's byte-length
and row-size rules.

## Backend-specific types

The backend ships MariaDB-only column types under
`rhosocial.activerecord.backend.impl.mariadb.types`, plus expression nodes under
`...impl.mariadb.expression`. Representative families:

| Family | Examples | Notes |
|--------|----------|-------|
| Numeric | `TINYINT`, `MEDIUMINT`, `BIGINT`, `SERIAL`, `BIT(M)` | `SERIAL` is `BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE` |
| Text | `TINYTEXT`, `MEDIUMTEXT`, `LONGTEXT`, `ENUM`, `SET` | `SET` has its own expression/functions family |
| Binary | `BINARY`, `VARBINARY`, `BLOB` variants | `bytes` values pass through `MariaDBBlobAdapter` |
| Temporal | `DATETIME(fsp)`, `TIMESTAMP(fsp)`, `YEAR` | Fractional seconds precision is supported via `fsp` |
| JSON | `JSON` (stored as `LONGTEXT`) | From 10.4.3 a `CHECK (json_valid(...))` is installed automatically |
| Spatial | `GEOMETRY`, `POINT`, `LINESTRING`, `POLYGON`, … | Rendered by the spatial expression family; SRID is exposed by introspection |
| UUID | `UUID` | Native type from 10.7; `MariaDBUUIDAdapter` also handles `CHAR(36)` / `BINARY(16)` |
| System versioning | `WITH SYSTEM VERSIONING` row period columns | From 10.3 |

## Version-sensitive types

Several types only exist from a certain release; the type renderer consults the
same boundary table used by the dialect gates:

- `JSON` validation check: 10.4.3
- `UUID` native type: 10.7
- `XMLTYPE`: 12.3

When a type is unavailable, the renderer either falls back to its storage
equivalent (for example JSON → `LONGTEXT` before 10.4.3) or reports the feature
as unsupported — it never silently emits syntax the server will reject. See
[Version gates](version_gates.md).

## Type adapters

Conversions for `bytes`, `dict`/`list` (JSON), `UUID`, `Decimal`, spatial values,
bit strings and temporal types live in `...impl.mariadb.adapters`. See
[Type adapters](../type_adapters/README.md) for the conversion rules and how to
register a custom adapter.
