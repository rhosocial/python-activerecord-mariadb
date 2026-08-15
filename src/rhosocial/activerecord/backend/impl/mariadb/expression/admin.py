# src/rhosocial/activerecord/backend/impl/mariadb/expression/admin.py
"""MariaDB administrative statement expressions.

These cover instance-level, security, and account management commands:

- FLUSH [NO_WRITE_TO_BINLOG | LOCAL] option [, option ...]
- KILL [CONNECTION | QUERY] processlist_id
- SHUTDOWN
- CREATE / ALTER / DROP USER
- CREATE / DROP ROLE
- GRANT ... ON ... TO ... [WITH GRANT OPTION]
- REVOKE ... ON ... FROM ...
- DENY ... ON ... TO ... (MariaDB 13.1+)
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class FlushOption(Enum):
    """FLUSH statement options."""

    TABLES = "TABLES"
    TABLES_WITH_READ_LOCK = "TABLES WITH READ LOCK"
    LOGS = "LOGS"
    PRIVILEGES = "PRIVILEGES"
    BINARY_LOGS = "BINARY LOGS"
    ENGINE_LOGS = "ENGINE LOGS"
    ERROR_LOGS = "ERROR LOGS"
    GENERAL_LOGS = "GENERAL LOGS"
    HOSTS = "HOSTS"
    OPTIMIZER_COSTS = "OPTIMIZER_COSTS"
    RELAY_LOGS = "RELAY LOGS"
    SLOW_LOGS = "SLOW LOGS"
    STATUS = "STATUS"
    USER_RESOURCES = "USER_RESOURCES"
    QUERY_CACHE = "QUERY CACHE"
    DES_KEY_FILE = "DES_KEY_FILE"
    MASTER = "MASTER"
    REPLICA = "REPLICA"
    SLAVE = "SLAVE"


class KillTarget(Enum):
    """KILL target selector."""

    CONNECTION = "CONNECTION"
    QUERY = "QUERY"


class MariaDBFlushExpression(BaseExpression):
    """Represent ``FLUSH`` with one or more options."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        options: List[FlushOption],
        *,
        no_write_to_binlog: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.options: List[FlushOption] = list(options)
        self.no_write_to_binlog: bool = no_write_to_binlog
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        if not strict:
            return
        if not self.options:
            raise ValueError("FLUSH requires at least one option")

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_flush_statement(self)


class MariaDBKillExpression(BaseExpression):
    """Represent ``KILL [CONNECTION | QUERY] processlist_id``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        processlist_id: int,
        target: KillTarget = KillTarget.CONNECTION,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.processlist_id: int = processlist_id
        self.target: KillTarget = target
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_kill_statement(self)


class MariaDBShutdownExpression(BaseExpression):
    """Represent the ``SHUTDOWN`` statement."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_shutdown_statement(self)


class AccountSpec:
    """Represent a ``'user'@'host'`` account specification."""

    def __init__(self, user: str, host: str = "%"):
        self.user: str = user
        self.host: str = host

    def __repr__(self) -> str:  # pragma: no cover
        return f"AccountSpec(user={self.user!r}, host={self.host!r})"


class MariaDBCreateUserExpression(BaseExpression):
    """Represent ``CREATE USER [IF NOT EXISTS] 'user'@'host' [IDENTIFIED BY ...]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        accounts: List[AccountSpec],
        *,
        if_not_exists: bool = False,
        identified_by: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.accounts: List[AccountSpec] = list(accounts)
        self.if_not_exists: bool = if_not_exists
        self.identified_by: Optional[str] = identified_by
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_user_statement(self)


class MariaDBAlterUserExpression(BaseExpression):
    """Represent ``ALTER USER [IF EXISTS] 'user'@'host' [IDENTIFIED BY ...]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        accounts: List[AccountSpec],
        *,
        if_exists: bool = False,
        identified_by: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.accounts: List[AccountSpec] = list(accounts)
        self.if_exists: bool = if_exists
        self.identified_by: Optional[str] = identified_by
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_alter_user_statement(self)


class MariaDBDropUserExpression(BaseExpression):
    """Represent ``DROP USER [IF EXISTS] 'user'@'host' [, ...]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        accounts: List[AccountSpec],
        *,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.accounts: List[AccountSpec] = list(accounts)
        self.if_exists: bool = if_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_user_statement(self)


class MariaDBCreateRoleExpression(BaseExpression):
    """Represent ``CREATE ROLE [IF NOT EXISTS] role [, role ...]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        roles: List[str],
        *,
        if_not_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.roles: List[str] = list(roles)
        self.if_not_exists: bool = if_not_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_create_role_statement(self)


class MariaDBDropRoleExpression(BaseExpression):
    """Represent ``DROP ROLE [IF EXISTS] role [, role ...]``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        roles: List[str],
        *,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.roles: List[str] = list(roles)
        self.if_exists: bool = if_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_drop_role_statement(self)


class GrantPrivilege:
    """Represent a privilege grant for ``GRANT`` / ``REVOKE`` / ``DENY``.

    Attributes:
        privilege: Privilege name, e.g. ``SELECT``, ``ALL PRIVILEGES``.
        columns: Optional column list.
    """

    def __init__(self, privilege: str, columns: Optional[List[str]] = None):
        self.privilege: str = privilege
        self.columns: List[str] = list(columns or [])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"GrantPrivilege(privilege={self.privilege!r},"
            f" columns={self.columns!r})"
        )


class MariaDBGrantExpression(BaseExpression):
    """Represent ``GRANT [OR REPLACE] [IF EXISTS] priv_list ON object TO accounts``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        privileges: List[GrantPrivilege],
        accounts: List[AccountSpec],
        *,
        on_object: Optional[str] = None,
        with_grant_option: bool = False,
        or_replace: bool = False,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.privileges: List[GrantPrivilege] = list(privileges)
        self.accounts: List[AccountSpec] = list(accounts)
        self.on_object: Optional[str] = on_object  # default "*.*"
        self.with_grant_option: bool = with_grant_option
        self.or_replace: bool = or_replace
        self.if_exists: bool = if_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_grant_statement(self)


class MariaDBRevokeExpression(BaseExpression):
    """Represent ``REVOKE [IF EXISTS] priv_list ON object FROM accounts``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        privileges: List[GrantPrivilege],
        accounts: List[AccountSpec],
        *,
        on_object: Optional[str] = None,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.privileges: List[GrantPrivilege] = list(privileges)
        self.accounts: List[AccountSpec] = list(accounts)
        self.on_object: Optional[str] = on_object
        self.if_exists: bool = if_exists
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_revoke_statement(self)


class MariaDBDenyExpression(BaseExpression):
    """Represent ``DENY priv_list ON object TO accounts`` (MariaDB 13.1+)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        privileges: List[GrantPrivilege],
        accounts: List[AccountSpec],
        *,
        on_object: Optional[str] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.privileges: List[GrantPrivilege] = list(privileges)
        self.accounts: List[AccountSpec] = list(accounts)
        self.on_object: Optional[str] = on_object
        self.dialect_options: Dict[str, Any] = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_deny_statement(self)
