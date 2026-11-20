<!-- docs/en_US/type_adapters/custom.md -->
# Custom adapters

When a column stores a Python value in a non-default form, write an adapter by
subclassing the core `SQLTypeAdapter` and registering it with the backend.

## Adapter shape

```python
from typing import Any, Dict, List, Optional, Type

from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class MoneyAdapter(SQLTypeAdapter):
    """Store an amount in minor units (cents) as a BIGINT."""

    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Money: [int]}

    def to_database(self, value, target_type, options=None):
        if value is None:
            return None
        return value.minor_units

    def from_database(self, value, target_type, options=None, **kwargs):
        if value is None:
            return None
        return Money.from_minor_units(int(value))
```

`supported_types` maps a Python class to the database target types it can
produce. Both directions must handle `None`. The `options` dict carries any
column-level hints the backend passes through; `from_database` additionally
receives keyword context such as the column name.

## Registration

Register the adapter on the backend (or through the model's field declaration,
depending on the core API version you target). The
[core adapter guide](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US)
documents the registration entry point; the contract is identical here — only
the set of built-in adapters differs.

```python
backend.register_type_adapter(MoneyAdapter())
```

## Reusing core base classes

The core exposes ready-made base classes for common wire formats:

- `BitStringAdapterBase` — `BIT(M)`
- `GeometryAdapterBase` — spatial WKB
- `MacAddressAdapterBase` — MAC address text/integer
- `RangeAdapterBase` — range and multirange values
- `VectorAdapterBase` — vector columns

This backend subclasses those for MariaDB (`MariaDBBlobAdapter`,
`MariaDBJSONAdapter`, `MariaDBUUIDAdapter`, and the bit/geometry/range/vector
adapters). Extend them rather than starting from scratch when your type is a
variation of one of these.

## Rules of thumb

1. Keep adapters stateless, or at least safe to share across connections.
2. Do not silently round — prefer raising on a value that cannot be represented
   exactly.
3. Test both directions with `None`, the smallest and largest legal values, and
   a real MariaDB round-trip.
