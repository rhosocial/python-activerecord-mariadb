# src/rhosocial/activerecord/backend/impl/mariadb/protocols/admin.py
"""MariaDB administrative / account management protocol."""

from typing import TYPE_CHECKING, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.impl.mariadb.expression.admin import (
        MariaDBAlterUserExpression,
        MariaDBCreateRoleExpression,
        MariaDBCreateUserExpression,
        MariaDBDenyExpression,
        MariaDBDropRoleExpression,
        MariaDBDropUserExpression,
        MariaDBFlushExpression,
        MariaDBGrantExpression,
        MariaDBKillExpression,
        MariaDBRevokeExpression,
        MariaDBShutdownExpression,
    )


@runtime_checkable
class MariaDBAdminSupport(Protocol):
    """MariaDB administrative / account management support protocol.

    Feature Source: Native support (all versions unless noted)

    Covers FLUSH, KILL, SHUTDOWN, CREATE/ALTER/DROP USER, CREATE/DROP ROLE,
    GRANT/REVOKE, and DENY.

    Official Documentation:
    - FLUSH: https://mariadb.com/kb/en/flush/
    - KILL: https://mariadb.com/kb/en/kill/
    - SHUTDOWN: https://mariadb.com/kb/en/shutdown/
    - CREATE USER: https://mariadb.com/kb/en/create-user/
    - CREATE ROLE: https://mariadb.com/kb/en/create-role/
    - GRANT: https://mariadb.com/kb/en/grant/
    - REVOKE: https://mariadb.com/kb/en/revoke/
    - DENY: https://mariadb.com/kb/en/deny/
    """

    def supports_flush(self) -> bool:
        """Whether FLUSH is supported."""
        ...

    def supports_kill(self) -> bool:
        """Whether KILL is supported."""
        ...

    def supports_shutdown(self) -> bool:
        """Whether SHUTDOWN is supported."""
        ...

    def supports_create_user(self) -> bool:
        """Whether CREATE USER is supported."""
        ...

    def supports_alter_user(self) -> bool:
        """Whether ALTER USER is supported."""
        ...

    def supports_drop_user(self) -> bool:
        """Whether DROP USER is supported."""
        ...

    def supports_create_role(self) -> bool:
        """Whether CREATE ROLE is supported."""
        ...

    def supports_drop_role(self) -> bool:
        """Whether DROP ROLE is supported."""
        ...

    def supports_grant(self) -> bool:
        """Whether GRANT is supported."""
        ...

    def supports_grant_or_replace(self) -> bool:
        """Whether GRANT OR REPLACE is supported (MariaDB 10.1.4+)."""
        ...

    def supports_grant_if_exists(self) -> bool:
        """Whether GRANT/REVOKE IF EXISTS is supported (MariaDB 10.1.4+)."""
        ...

    def supports_revoke(self) -> bool:
        """Whether REVOKE is supported."""
        ...

    def supports_deny(self) -> bool:
        """Whether DENY is supported (MariaDB 13.1+)."""
        ...

    def format_flush_statement(self, expr: "MariaDBFlushExpression") -> Tuple[str, tuple]:
        """Format FLUSH."""
        ...

    def format_kill_statement(self, expr: "MariaDBKillExpression") -> Tuple[str, tuple]:
        """Format KILL."""
        ...

    def format_shutdown_statement(
        self,
        expr: "MariaDBShutdownExpression",
    ) -> Tuple[str, tuple]:
        """Format SHUTDOWN."""
        ...

    def format_create_user_statement(
        self,
        expr: "MariaDBCreateUserExpression",
    ) -> Tuple[str, tuple]:
        """Format CREATE USER."""
        ...

    def format_alter_user_statement(
        self,
        expr: "MariaDBAlterUserExpression",
    ) -> Tuple[str, tuple]:
        """Format ALTER USER."""
        ...

    def format_drop_user_statement(
        self,
        expr: "MariaDBDropUserExpression",
    ) -> Tuple[str, tuple]:
        """Format DROP USER."""
        ...

    def format_create_role_statement(
        self,
        expr: "MariaDBCreateRoleExpression",
    ) -> Tuple[str, tuple]:
        """Format CREATE ROLE."""
        ...

    def format_drop_role_statement(
        self,
        expr: "MariaDBDropRoleExpression",
    ) -> Tuple[str, tuple]:
        """Format DROP ROLE."""
        ...

    def format_grant_statement(
        self,
        expr: "MariaDBGrantExpression",
    ) -> Tuple[str, tuple]:
        """Format GRANT."""
        ...

    def format_revoke_statement(
        self,
        expr: "MariaDBRevokeExpression",
    ) -> Tuple[str, tuple]:
        """Format REVOKE."""
        ...

    def format_deny_statement(
        self,
        expr: "MariaDBDenyExpression",
    ) -> Tuple[str, tuple]:
        """Format DENY."""
        ...
