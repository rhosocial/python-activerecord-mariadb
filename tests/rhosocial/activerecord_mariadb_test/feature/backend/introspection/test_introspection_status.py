# tests/rhosocial/activerecord_mariadb_test/feature/backend/introspection/test_introspection_status.py
"""Offline tests for the introspector ``status`` property (lazy creation)."""
from rhosocial.activerecord.backend.impl.mariadb import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig
from rhosocial.activerecord.backend.impl.mariadb.introspection import (
    SyncMariaDBIntrospector,
    AsyncMariaDBIntrospector,
)


def make_config(**overrides) -> MariaDBConnectionConfig:
    params = dict(host="localhost", port=3306, database="test", username="root", password="")
    params.update(overrides)
    return MariaDBConnectionConfig(**params)


def make_introspector() -> SyncMariaDBIntrospector:
    backend = MariaDBBackend(connection_config=make_config())
    return SyncMariaDBIntrospector(backend, executor=object())


class TestSyncStatusProperty:
    def test_status_is_lazily_created(self):
        introspector = make_introspector()
        assert introspector._status_instance is None
        status = introspector.status
        assert status is not None
        assert introspector._status_instance is status

    def test_show_is_separate_from_status(self):
        introspector = make_introspector()
        show = introspector.show
        status = introspector.status
        assert show is not None
        assert status is not None
        assert show is not status


class TestAsyncStatusProperty:
    def test_async_status_is_lazily_created(self):
        backend = MariaDBBackend(connection_config=make_config())
        introspector = AsyncMariaDBIntrospector(backend, executor=object())
        assert introspector._status_instance is None
        status = introspector.status
        assert status is not None
        assert introspector._status_instance is status