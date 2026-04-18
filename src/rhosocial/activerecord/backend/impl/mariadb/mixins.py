# src/rhosocial/activerecord/backend/impl/mariadb/mixins.py
"""
MariaDB dialect-specific Mixin implementations.

This module provides backward compatibility by re-exporting all mixins
from the modular mixins/ subdirectory.

For new code, import directly from the mixins subdirectory:
    from rhosocial.activerecord.backend.impl.mariadb.mixins import (
        MariaDBSequenceMixin,
        MariaDBReturningMixin,
        ...
    )

The mixins are organized as follows:
- introspection.py: Database metadata introspection
- transaction.py: Transaction isolation level management
- backend.py: Backend common functionality and version boundaries
- sequence.py: SEQUENCE storage engine support (MariaDB 10.3+)
- returning.py: RETURNING clause support (MariaDB 10.5+)
- system_versioning.py: System-versioned tables (MariaDB 10.3+)
- dml.py: DML operations (INSERT IGNORE, REPLACE, LOAD DATA)
- spatial.py: Spatial data types and functions
- locking.py: Row-level locking (FOR UPDATE, FOR SHARE, SKIP LOCKED)
- trigger.py: Trigger DDL with INSTEAD OF support (MariaDB 10.4+)
- json.py: JSON functions and arrow operators
"""

# Import from modular mixins subdirectory
from .mixins import (
    MARIADB_VERSION_BOUNDARIES,
    MariaDBIntrospectionMixin,
    MariaDBTransactionMixin,
    MariaDBBackendMixin,
    MariaDBSequenceMixin,
    MariaDBReturningMixin,
    MariaDBSystemVersioningMixin,
    MariaDBDMLOperationMixin,
    MariaDBSpatialMixin,
    MariaDBLockingMixin,
    MariaDBTriggerMixin,
    MariaDBJSONMixin,
)

__all__ = [
    'MARIADB_VERSION_BOUNDARIES',
    'MariaDBIntrospectionMixin',
    'MariaDBTransactionMixin',
    'MariaDBBackendMixin',
    'MariaDBSequenceMixin',
    'MariaDBReturningMixin',
    'MariaDBSystemVersioningMixin',
    'MariaDBDMLOperationMixin',
    'MariaDBSpatialMixin',
    'MariaDBLockingMixin',
    'MariaDBTriggerMixin',
    'MariaDBJSONMixin',
]
