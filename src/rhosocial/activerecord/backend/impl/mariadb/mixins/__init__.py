# src/rhosocial/activerecord/backend/impl/mariadb/mixins/__init__.py
"""MariaDB dialect-specific Mixin implementations.

This module provides modular mixin classes that implement MariaDB-specific
functionality shared between sync and async backends.

Mixin Organization:
- introspection.py: Database metadata introspection
- transaction.py: Transaction isolation level management
- backend.py: Backend common functionality
- sequence.py: SEQUENCE storage engine support (MariaDB 10.3+)
- returning.py: RETURNING clause support (MariaDB 10.5+)
- system_versioning.py: System-versioned tables (MariaDB 10.3+)
- dml.py: DML operations (INSERT IGNORE, REPLACE, LOAD DATA)
- spatial.py: Spatial data types and functions
- locking.py: Row-level locking (FOR UPDATE, FOR SHARE, SKIP LOCKED)
- trigger.py: Trigger DDL with INSTEAD OF support (MariaDB 10.4+)
- json.py: JSON functions and arrow operators
- set_type.py: SET type support
- fulltext.py: Full-text search support
- intersect_except.py: INTERSECT/EXCEPT set operations
- cte.py: Common Table Expressions support
- window.py: Window functions support
"""

from .introspection import MariaDBIntrospectionMixin
from .transaction import MariaDBTransactionMixin
from .backend import MariaDBBackendMixin, MARIADB_VERSION_BOUNDARIES
from .sequence import MariaDBSequenceMixin
from .returning import MariaDBReturningMixin
from .system_versioning import MariaDBSystemVersioningMixin
from .dml import MariaDBDMLOperationMixin
from .spatial import MariaDBSpatialMixin
from .locking import MariaDBLockingMixin
from .trigger import MariaDBTriggerMixin
from .json import MariaDBJSONMixin
from .fulltext_search import MariaDBFullTextSearchMixin
from .table import MariaDBTableMixin
from .set_type import MariaDBSetTypeMixin
from .modify_column import MariaDBModifyColumnMixin
from .concurrency import MariaDBConcurrencyMixin, AsyncMariaDBConcurrencyMixin
from .partition import MariaDBPartitionMixin
from .types import MariaDBTypeSupportMixin
from .rename_table import MariaDBRenameTableMixin
from .truncate import MariaDBTruncateMixin
from .ddl.column import MariaDBAlterColumnModifierMixin
from .ddl.constraint import MariaDBAlterConstraintModifierMixin
from .ddl.alter_table import MariaDBAlterTableMixin
from .ddl.maintenance import MariaDBMaintenanceMixin
from .ddl.routine import MariaDBRoutineMixin
from .ddl.admin import MariaDBAdminMixin

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
    'MariaDBFullTextSearchMixin',
    'MariaDBTableMixin',
    'MariaDBSetTypeMixin',
    'MariaDBModifyColumnMixin',
    'MariaDBConcurrencyMixin',
    'AsyncMariaDBConcurrencyMixin',
    'MariaDBPartitionMixin',
    'MariaDBTypeSupportMixin',
    'MariaDBAlterColumnModifierMixin',
    'MariaDBAlterConstraintModifierMixin',
    'MariaDBRenameTableMixin',
    'MariaDBTruncateMixin',
    'MariaDBAlterTableMixin',
    'MariaDBMaintenanceMixin',
    'MariaDBRoutineMixin',
    'MariaDBAdminMixin',
]
