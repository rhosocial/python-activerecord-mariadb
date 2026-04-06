# src/rhosocial/activerecord/backend/impl/mariadb/show/types.py
"""
MariaDB SHOW command result types.

This module defines data classes for the results of MariaDB SHOW commands.
MariaDB SHOW command results are fully compatible with MySQL SHOW command results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ShowCreateTableResult:
    """Result of SHOW CREATE TABLE command."""

    table_name: str
    create_statement: str


@dataclass
class ShowCreateViewResult:
    """Result of SHOW CREATE VIEW command."""

    view_name: str
    create_statement: str
    character_set_client: Optional[str] = None
    collation_connection: Optional[str] = None


@dataclass
class ShowCreateTriggerResult:
    """Result of SHOW CREATE TRIGGER command."""

    trigger_name: str
    create_statement: str
    character_set_client: Optional[str] = None
    collation_connection: Optional[str] = None
    database_collation: Optional[str] = None


@dataclass
class ShowColumnResult:
    """Result row from SHOW COLUMNS command."""

    field: str
    type: str
    null: str
    key: Optional[str] = None
    default: Optional[Any] = None
    extra: Optional[str] = None
    privileges: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ShowIndexResult:
    """Result row from SHOW INDEX command."""

    table: str
    non_unique: int
    key_name: str
    seq_in_index: int
    column_name: str
    collation: Optional[str] = None
    cardinality: Optional[int] = None
    sub_part: Optional[int] = None
    packed: Optional[str] = None
    null: Optional[str] = None
    index_type: str = "BTREE"
    comment: Optional[str] = None
    index_comment: Optional[str] = None
    visible: Optional[str] = None
    expression: Optional[str] = None


@dataclass
class ShowTableResult:
    """Result row from SHOW TABLES command."""

    name: str
    table_type: Optional[str] = None


@dataclass
class ShowDatabaseResult:
    """Result row from SHOW DATABASES command."""

    name: str


@dataclass
class ShowTableStatusResult:
    """Result row from SHOW TABLE STATUS command."""

    name: str
    engine: Optional[str] = None
    version: Optional[int] = None
    row_format: Optional[str] = None
    rows: Optional[int] = None
    avg_row_length: Optional[int] = None
    data_length: Optional[int] = None
    max_data_length: Optional[int] = None
    index_length: Optional[int] = None
    data_free: Optional[int] = None
    auto_increment: Optional[int] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    check_time: Optional[str] = None
    collation: Optional[str] = None
    checksum: Optional[int] = None
    create_options: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ShowTriggerResult:
    """Result row from SHOW TRIGGERS command."""

    trigger: str
    event: str
    table: str
    statement: str
    timing: str
    created: Optional[str] = None
    sql_mode: Optional[str] = None
    definer: Optional[str] = None
    character_set_client: Optional[str] = None
    collation_connection: Optional[str] = None
    database_collation: Optional[str] = None


@dataclass
class ShowVariableResult:
    """Result row from SHOW VARIABLES command."""

    variable_name: str
    value: Optional[str] = None


@dataclass
class ShowStatusResult:
    """Result row from SHOW STATUS command."""

    variable_name: str
    value: Optional[str] = None


@dataclass
class ShowProcessListResult:
    """Result row from SHOW PROCESSLIST command."""

    id: int
    user: str
    host: str
    command: str
    time: Optional[int] = None
    db: Optional[str] = None
    state: Optional[str] = None
    info: Optional[str] = None


@dataclass
class ShowWarningResult:
    """Result row from SHOW WARNINGS/ERRORS command."""

    level: str
    code: int
    message: str


@dataclass
class ShowEngineResult:
    """Result row from SHOW ENGINES command."""

    engine: str
    support: str
    transactions: Optional[str] = None
    xa: Optional[str] = None
    savepoints: Optional[str] = None


@dataclass
class ShowCharsetResult:
    """Result row from SHOW CHARACTER SET command."""

    charset: str
    description: str
    default_collation: str
    maxlen: int


@dataclass
class ShowCollationResult:
    """Result row from SHOW COLLATION command."""

    collation: str
    charset: str
    id: int
    default: Optional[str] = None
    compiled: Optional[str] = None
    sortlen: Optional[int] = None


@dataclass
class ShowGrantResult:
    """Result row from SHOW GRANTS command."""

    grants: str


@dataclass
class ShowPluginResult:
    """Result row from SHOW PLUGINS command."""

    name: str
    status: str
    type: Optional[str] = None
    library: Optional[str] = None
    license: Optional[str] = None
