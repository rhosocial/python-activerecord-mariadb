# src/rhosocial/activerecord/backend/impl/mariadb/introspection/status_types.py
"""MariaDB's own server status families: the binary log and replication.

MariaDB answers the two families this module types, and no other engine
answers them the same way, so the families live here rather than in core's
``ServerOverview``: a slot on the core shape would assert on every other
backend that it has something it does not have
(``.claude/rules/introspection.md`` §5 -- ownership is decided by divergence,
and ``extra`` is not a place for another family's fields).

They are MariaDB types, not MySQL's. The two engines look like copies -- the
same SHOW vocabulary, the same result columns -- and the questions they
answer have drifted apart, so these two classes are written from what MariaDB
answers and carry only that. A field the sibling has and MariaDB does not is
absent, not ``None``-by-default: the absent field is the statement that this
engine was never asked.

Answers come from two shapes of command, both of them MariaDB's own:

- ``SHOW [GLOBAL] VARIABLES LIKE ...`` -- ``log_bin``, ``binlog_format``,
  ``gtid_binlog_pos``, ``gtid_strict_mode``, ``server_id``,
  ``log_slave_updates``;
- ``SHOW MASTER STATUS`` -- the current file, position, do/ignore
  databases and the executed GTID set;
- ``SHOW SLAVE STATUS`` -- the replica side, one row per configured
  replica.

``None`` on any field means "this server did not report it", never "off": the
collectors distinguish an answered ``OFF`` from a question the server
refused, and a caller must not turn ``None`` into a boolean.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.status import ServerOverview

__all__ = [
    "MariaDBBinaryLogInfo",
    "MariaDBReplicationInfo",
    "MariaDBServerOverview",
]


@dataclass
class MariaDBBinaryLogInfo:
    """The state of MariaDB's binary log, as a server with one reports it.

    Attributes:
        log_enabled: Whether binary logging is on (``log_bin``). ``None``
            when the variable was not reported.
        log_format: The row-events format (``binlog_format``): ``ROW``,
            ``STATEMENT`` or ``MIXED``.
        current_log_file: The file the server is writing (``SHOW MASTER
            STATUS`` ``File``). ``None`` when the answer set was empty --
            which is how MariaDB answers with ``log_bin`` off.
        current_log_position: The byte position inside that file.
        binlog_do_db: Databases whose changes are logged, when the server
            carries a filter. Empty means no filter, not an unread filter.
        binlog_ignore_db: Databases excluded from the log, same rule.
        executed_gtid_set: The domain-scoped GTID set the log covers, the
            ``Executed_Gtid_Set`` of ``SHOW MASTER STATUS``.
        gtid_binlog_pos: The same position as the variable MariaDB spells
            it: ``@@gtid_binlog_pos``. Carried beside the set because the
            variable is what a client matches the log against.
        gtid_strict_mode: Whether out-of-order GTID handling is strict.
        extra: Additional MariaDB-specific information.

    What is deliberately absent, because MariaDB has no command that
    answers it: there is no ``SHOW BINARY LOGS`` here, so the log's file
    *list* and its total *size* are not claimed -- only the current file
    exists in the vocabulary. MySQL's ``binlog_rows_query_log_events`` and
    ``binlog_checksum`` settings are likewise not MariaDB variables and are
    not reported.
    """

    log_enabled: Optional[bool] = None
    log_format: Optional[str] = None
    current_log_file: Optional[str] = None
    current_log_position: Optional[int] = None
    binlog_do_db: List[str] = field(default_factory=list)
    binlog_ignore_db: List[str] = field(default_factory=list)
    executed_gtid_set: Optional[str] = None
    gtid_binlog_pos: Optional[str] = None
    gtid_strict_mode: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MariaDBReplicationInfo:
    """MariaDB's replication state: the server's identity and its replica side.

    The family answers two questions the catalog can answer separately --
    "which server am I" and "is this server pulling events" -- and stops
    there. The master side is not a second class: what a master serves is
    the binary log, typed in :class:`MariaDBBinaryLogInfo`, and repeating
    the current file here would be a second copy of one fact.

    Galera is not here, and the reason is a fact about the answer rather
    than an omission: a Galera-enabled build reports its cluster state
    through ``wsrep_*`` variables and ``SHOW STATUS LIKE 'wsrep%'``, which
    a stock primary/replica server does not produce at all, and a replica
    of a Galera cluster is a ``SHOW SLAVE STATUS`` row like any other. A
    field the connected server cannot answer is not a fact this class can
    carry, so the cluster family stays unanswered until a server that has
    it reports it -- which a field on this class cannot arrange.

    Attributes:
        server_id: The replication identity the server replicates with
            (``server_id``). ``0`` is a valid answer and means "no
            identity", so it is kept rather than coerced to ``None``.
        log_slave_updates: Whether this server re-logs the events it
            applies (``log_slave_updates``) -- the setting that decides
            whether a replica is a master for the next tier.
        is_replica: ``True`` when ``SHOW SLAVE STATUS`` returned a row,
            ``False`` when it returned none. ``None`` when the question
            could not be asked.
        slave_io_running: The IO thread's state as MariaDB spells it
            (``Yes`` / ``No``), when a replica row was returned.
        slave_sql_running: The SQL thread's state, same spelling.
        master_host: The upstream this replica pulls from.
        master_port: The upstream's port.
        master_user: The account the replica authenticates with.
        seconds_behind_master: The replica's lag; ``None`` when the applier
            is not running and MariaDB reports nothing.
        master_log_file: The upstream log the IO thread is reading.
        read_master_log_pos: How far into that log it has read.
        relay_master_log_file: The upstream log the SQL thread applies.
        slave_io_state: The IO thread's textual state.
        last_io_errno / last_io_error: The IO thread's last failure.
        last_sql_errno / last_sql_error: The SQL thread's last failure.
        relay_log_file / relay_log_pos: The relay log and the position in it.
        exec_master_log_pos: How far the applier has executed.
        using_gtid: The GTID mode of the connection (``0`` / ``1`` /
            ``Current_Pos``), when reported.
        gtid_io_pos: The GTID position the IO thread has read to.
        extra: Additional MariaDB-specific information.
    """

    server_id: Optional[int] = None
    log_slave_updates: Optional[bool] = None
    is_replica: Optional[bool] = None
    slave_io_running: Optional[str] = None
    slave_sql_running: Optional[str] = None
    master_host: Optional[str] = None
    master_port: Optional[int] = None
    master_user: Optional[str] = None
    seconds_behind_master: Optional[int] = None
    master_log_file: Optional[str] = None
    read_master_log_pos: Optional[int] = None
    relay_master_log_file: Optional[str] = None
    slave_io_state: Optional[str] = None
    last_io_errno: Optional[int] = None
    last_io_error: Optional[str] = None
    last_sql_errno: Optional[int] = None
    last_sql_error: Optional[str] = None
    relay_log_file: Optional[str] = None
    relay_log_pos: Optional[int] = None
    exec_master_log_pos: Optional[int] = None
    using_gtid: Optional[str] = None
    gtid_io_pos: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MariaDBServerOverview(ServerOverview):
    """MariaDB's complete status overview: the core shape plus its own families.

    An LSP subclass of :class:`ServerOverview`, so ``get_overview()``'s core
    signature does not change -- the subclass is a legal covariant return --
    and ``to_dict()`` iterates the instance's fields rather than naming them,
    so the two MariaDB families below serialize without being re-declared
    here (``.claude/rules/introspection.md`` §5).

    The slots are this engine's own typed answers, each ``None`` until the
    introspector asked for it: a server with binary logging off reports
    ``binary_log.log_enabled is False`` rather than a missing object, and a
    server that replicates nothing reports ``replication.is_replica is
    False``.
    """

    binary_log: Optional[MariaDBBinaryLogInfo] = None
    replication: Optional[MariaDBReplicationInfo] = None
