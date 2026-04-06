# src/rhosocial/activerecord/backend/impl/mariadb/explain/__init__.py
"""MariaDB EXPLAIN result types module.

MariaDB 10.6+ supports EXPLAIN FORMAT=JSON/TREE/TRADITIONAL and EXPLAIN ANALYZE.
"""

from .types import MariaDBExplainRow, MariaDBExplainResult, MariaDBExplainJsonResult, MariaDBExplainAnalyzeResult

__all__ = [
    "MariaDBExplainRow",
    "MariaDBExplainResult",
    "MariaDBExplainJsonResult",
    "MariaDBExplainAnalyzeResult",
]
