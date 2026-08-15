# src/rhosocial/activerecord/backend/impl/mariadb/mixins/ddl/admin.py
"""MariaDB administrative / account management mixin.

MariaDB supports account management and instance-level commands with
extensions over the MySQL form:

    FLUSH [NO_WRITE_TO_BINLOG | LOCAL] option [, option ...]
    KILL [CONNECTION | QUERY] processlist_id
    SHUTDOWN
    CREATE USER [IF NOT EXISTS] acct [IDENTIFIED BY 'pwd']
    ALTER USER [IF EXISTS] acct [IDENTIFIED BY 'pwd']
    DROP USER [IF EXISTS] acct [, acct ...]
    CREATE ROLE [IF NOT EXISTS] role [, role ...]
    DROP ROLE [IF EXISTS] role [, role ...]
    GRANT [OR REPLACE] [IF EXISTS] priv ON obj TO acct [WITH GRANT OPTION]
    REVOKE [IF EXISTS] priv ON obj FROM acct
    DENY priv ON obj TO acct (MariaDB 13.1+)
"""
from typing import TYPE_CHECKING, Tuple

from ..backend import MARIADB_VERSION_BOUNDARIES
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

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


class MariaDBAdminMixin:
    """MariaDB administrative / account management command support."""

    # --- FLUSH ---

    def supports_flush(self) -> bool:
        return True

    def format_flush_statement(
        self,
        expr: "MariaDBFlushExpression",
    ) -> Tuple[str, tuple]:
        """Format ``FLUSH [NO_WRITE_TO_BINLOG|LOCAL] option [, option ...]``."""
        expr.validate(strict=self.strict_validation)
        parts = ["FLUSH"]
        if expr.no_write_to_binlog:
            parts.append("NO_WRITE_TO_BINLOG")
        parts.append(", ".join(option.value for option in expr.options))
        return " ".join(parts), ()

    # --- KILL ---

    def supports_kill(self) -> bool:
        return True

    def format_kill_statement(
        self,
        expr: "MariaDBKillExpression",
    ) -> Tuple[str, tuple]:
        """Format ``KILL [CONNECTION | QUERY] processlist_id``."""
        parts = ["KILL"]
        if expr.target.value:
            parts.append(expr.target.value)
        parts.append(str(int(expr.processlist_id)))
        return " ".join(parts), ()

    # --- SHUTDOWN ---

    def supports_shutdown(self) -> bool:
        return True

    def format_shutdown_statement(
        self,
        expr: "MariaDBShutdownExpression",
    ) -> Tuple[str, tuple]:
        """Format the ``SHUTDOWN`` statement."""
        return "SHUTDOWN", ()

    # --- Account management ---

    def supports_create_user(self) -> bool:
        return True

    def format_create_user_statement(
        self,
        expr: "MariaDBCreateUserExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE USER [IF NOT EXISTS] acct [IDENTIFIED BY 'pwd']``."""
        parts = ["CREATE USER"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(_format_accounts(self, expr.accounts))
        if expr.identified_by:
            parts.append(f"IDENTIFIED BY '{expr.identified_by}'")
        return " ".join(parts), ()

    def supports_alter_user(self) -> bool:
        return True

    def format_alter_user_statement(
        self,
        expr: "MariaDBAlterUserExpression",
    ) -> Tuple[str, tuple]:
        """Format ``ALTER USER [IF EXISTS] acct [IDENTIFIED BY 'pwd']``."""
        parts = ["ALTER USER"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(_format_accounts(self, expr.accounts))
        if expr.identified_by:
            parts.append(f"IDENTIFIED BY '{expr.identified_by}'")
        return " ".join(parts), ()

    def supports_drop_user(self) -> bool:
        return True

    def format_drop_user_statement(
        self,
        expr: "MariaDBDropUserExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP USER [IF EXISTS] acct [, acct ...]``."""
        parts = ["DROP USER"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(_format_accounts(self, expr.accounts))
        return " ".join(parts), ()

    def supports_create_role(self) -> bool:
        return True

    def format_create_role_statement(
        self,
        expr: "MariaDBCreateRoleExpression",
    ) -> Tuple[str, tuple]:
        """Format ``CREATE ROLE [IF NOT EXISTS] role [, role ...]``."""
        parts = ["CREATE ROLE"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        roles = ", ".join(self.format_identifier(r) for r in expr.roles)
        parts.append(roles)
        return " ".join(parts), ()

    def supports_drop_role(self) -> bool:
        return True

    def format_drop_role_statement(
        self,
        expr: "MariaDBDropRoleExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DROP ROLE [IF EXISTS] role [, role ...]``."""
        parts = ["DROP ROLE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        roles = ", ".join(self.format_identifier(r) for r in expr.roles)
        parts.append(roles)
        return " ".join(parts), ()

    # --- GRANT / REVOKE / DENY ---

    def supports_grant(self) -> bool:
        return True

    def supports_grant_or_replace(self) -> bool:
        """Whether ``GRANT OR REPLACE`` is supported.

        MariaDB 10.1.4+ supports ``GRANT OR REPLACE``.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['GRANT_OR_REPLACE']

    def supports_grant_if_exists(self) -> bool:
        """Whether ``GRANT IF EXISTS`` / ``REVOKE IF EXISTS`` is supported.

        MariaDB 10.1.4+ supports ``GRANT IF EXISTS`` and ``REVOKE IF EXISTS``.
        """
        return self.version >= MARIADB_VERSION_BOUNDARIES['GRANT_IF_EXISTS']

    def supports_deny(self) -> bool:
        """Whether ``DENY`` is supported (MariaDB 13.1+)."""
        return self.version >= MARIADB_VERSION_BOUNDARIES['DENY']

    def format_grant_statement(
        self,
        expr: "MariaDBGrantExpression",
    ) -> Tuple[str, tuple]:
        """Format ``GRANT [OR REPLACE] [IF EXISTS] priv ON obj TO acct``."""
        parts = ["GRANT"]
        if expr.or_replace:
            if not self.supports_grant_or_replace():
                raise UnsupportedFeatureError(
                    self.name,
                    "GRANT OR REPLACE",
                    "GRANT OR REPLACE requires MariaDB 10.1.4 or later."
                )
            parts.append("OR REPLACE")
        if expr.if_exists:
            if not self.supports_grant_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "GRANT IF EXISTS",
                    "GRANT IF EXISTS requires MariaDB 10.1.4 or later."
                )
            parts.append("IF EXISTS")
        parts.append(_format_privileges(self, expr.privileges))
        parts.append("ON")
        parts.append(expr.on_object or "*.*")
        parts.append("TO")
        parts.append(_format_accounts(self, expr.accounts))
        if expr.with_grant_option:
            parts.append("WITH GRANT OPTION")
        return " ".join(parts), ()

    def supports_revoke(self) -> bool:
        return True

    def format_revoke_statement(
        self,
        expr: "MariaDBRevokeExpression",
    ) -> Tuple[str, tuple]:
        """Format ``REVOKE [IF EXISTS] priv ON obj FROM acct``."""
        parts = ["REVOKE"]
        if expr.if_exists:
            if not self.supports_grant_if_exists():
                raise UnsupportedFeatureError(
                    self.name,
                    "REVOKE IF EXISTS",
                    "REVOKE IF EXISTS requires MariaDB 10.1.4 or later."
                )
            parts.append("IF EXISTS")
        parts.append(_format_privileges(self, expr.privileges))
        parts.append("ON")
        parts.append(expr.on_object or "*.*")
        parts.append("FROM")
        parts.append(_format_accounts(self, expr.accounts))
        return " ".join(parts), ()

    def format_deny_statement(
        self,
        expr: "MariaDBDenyExpression",
    ) -> Tuple[str, tuple]:
        """Format ``DENY priv ON obj TO acct`` (MariaDB 13.1+)."""
        if not self.supports_deny():
            raise UnsupportedFeatureError(
                self.name,
                "DENY",
                "DENY requires MariaDB 13.1 or later."
            )
        parts = ["DENY"]
        parts.append(_format_privileges(self, expr.privileges))
        parts.append("ON")
        parts.append(expr.on_object or "*.*")
        parts.append("TO")
        parts.append(_format_accounts(self, expr.accounts))
        return " ".join(parts), ()


def _format_accounts(dialect, accounts) -> str:
    """Format account specifications as ``'user'@'host'``."""
    parts = []
    for acct in accounts:
        host = acct.host if acct.host else "%"
        parts.append(f"'{acct.user}'@'{host}'")
    return ", ".join(parts)


def _format_privileges(dialect, privileges) -> str:
    """Format a privilege list, optionally with column lists."""
    priv_parts = []
    for p in privileges:
        if p.columns:
            cols = ", ".join(dialect.format_identifier(c) for c in p.columns)
            priv_parts.append(f"{p.privilege} ({cols})")
        else:
            priv_parts.append(p.privilege)
    return ", ".join(priv_parts)
