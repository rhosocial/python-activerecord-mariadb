<!-- docs/en_US/type_adapters/README.md -->
# Type Adapters

Type adapters translate values between Python and MariaDB at the driver
boundary. The core defines the adapter protocol; this backend supplies the
MariaDB implementations in `...impl.mariadb.adapters`.

## Chapters

- [Type mapping](mapping.md) — the Python ↔ MariaDB conversion table
- [Custom adapters](custom.md) — registering your own conversions
- [Timezone handling](timezone.md) — temporal values

## Why adapters matter

A model field's Python annotation is not always the value the connector accepts:
a `dict` must become a JSON string, a `UUID` must become `CHAR(36)` or
`BINARY(16)`, a `Decimal` must survive MariaDB's numeric rendering, and a
spatial value needs WKB. Adapters centralise those decisions so models stay
declarative.

## Where they live

| Module | Contents |
|--------|----------|
| `adapters.py` | BLOB, JSON, UUID, Decimal, bit string, spatial, geometry, range and vector adapters |
| `types.py` | MariaDB column type renderers |
| `backend/adapters` (core) | Base classes such as `SQLTypeAdapter`, `BitString`, `Geometry`, `Range`, `Vector` |

The generic adapter contract and registration API are documented in the
[core library manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
