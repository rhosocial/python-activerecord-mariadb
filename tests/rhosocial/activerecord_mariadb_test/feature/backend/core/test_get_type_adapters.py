# tests/rhosocial/activerecord_mariadb_test/feature/backend/core/test_get_type_adapters.py
"""DB-free checks for the MariaDB backend's type adapter inventory.

Nothing here connects to a server: the backend registers its adapters in
``__init__``, so the inventory is complete before any I/O. What is pinned is
that the backend satisfies :class:`TypeAdapterCatalogProtocol`, that the list
has one entry per adapter class, and that the order is deterministic without
``get_default_adapter_suggestions`` losing its meaning.
"""

import pytest
from rhosocial.activerecord.backend.type_adapter import TypeAdapterCatalogProtocol

from rhosocial.activerecord.backend.impl.mariadb.backend import (
    AsyncMariaDBBackend,
    MariaDBBackend,
)


def _adapter_keys(adapters):
    return [(adapter.__class__.__module__, adapter.__class__.__qualname__) for adapter in adapters]


@pytest.fixture(params=[MariaDBBackend, AsyncMariaDBBackend], ids=["sync", "async"])
def backend(request):
    """Instantiate the backend without connecting to a server."""
    return request.param(version=(11, 4, 2), host="localhost", database="test")


class TestGetTypeAdapters:
    def test_backend_satisfies_catalog_protocol(self, backend):
        assert isinstance(backend, TypeAdapterCatalogProtocol)

    def test_inventory_is_non_empty(self, backend):
        adapters = backend.get_type_adapters()
        assert adapters
        assert all(hasattr(adapter, "supported_types") for adapter in adapters)

    def test_inventory_is_unique_by_adapter_class(self, backend):
        keys = _adapter_keys(backend.get_type_adapters())
        assert len(keys) == len(set(keys))

    def test_inventory_order_is_deterministic(self, backend):
        first = _adapter_keys(backend.get_type_adapters())
        second = _adapter_keys(backend.get_type_adapters())
        assert first == second == sorted(first)

    def test_each_call_returns_a_new_list(self, backend):
        first = backend.get_type_adapters()
        second = backend.get_type_adapters()
        assert first is not second

    def test_default_adapter_suggestions_are_still_provided(self, backend):
        suggestions = backend.get_default_adapter_suggestions()
        assert isinstance(suggestions, dict)
        assert suggestions
        assert all(isinstance(value, tuple) and len(value) == 2 for value in suggestions.values())
