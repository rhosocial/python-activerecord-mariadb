# src/rhosocial/activerecord/backend/impl/mariadb/mixins/namespace.py
"""Which namespace levels a MariaDB name may carry, and how MariaDB spells it.

MariaDB's qualified name is ``catalog`.`name``: the database occupies the
outer slot and there is no inner schema. That is the whole of this backend's
naming story, and it is said once, here.

Two things live here, and core keeps them separate on purpose:

* :meth:`supports_catalog` and :meth:`supports_catalog_qualification` answer
  which levels a name may carry.
* :meth:`format_qualified_name` spells the name.

The splitting matters because core used to decide the shape. One method,
``render_namespace``, both checked the levels and joined them, and its two
hard-coded slots -- catalog first, then schema -- happened to fit MariaDB only
because MariaDB has one level and the inner slot stayed empty. Oracle, which
has an inner schema and no catalog, fitted the same shape for the opposite
reason. That is a shape that happens to accommodate this engine, not one that
describes it. Naming the levels is what made the difference visible, so
MariaDB now names them: it lists a database and nothing else, and joining a
schema onto the name is left to ``validate_namespace`` to refuse.

The rendering half used to be unreachable from here. Every object kind carries
its own ``format_<kind>_object`` -- supplied by core's ``TableNameMixin``,
``IndexNameMixin`` and the rest -- and those ask this mixin for the levels.

The inner one is absent on purpose. ``supports_schema_qualification`` is left
at core's ``False``, and ``format_qualified_name`` below never reads
``schema_name``: a name carrying one is refused before the spelling runs, so a
second level here would be a spelling nothing can reach. ``supports_schema``
-- the DDL-side switch owned by :class:`SchemaMixin`, answering whether
``CREATE SCHEMA`` exists -- is a different question and lives in core's
``mixins/ddl_schema.py``. MariaDB's ``CREATE SCHEMA`` is a synonym for
``CREATE DATABASE`` rather than a second namespace layer, so this backend
leaves that switch at core's default as well.

Note that ``mixins/schema.py`` in this backend answers the DDL question
``True``, but nothing mixes it into :class:`~...dialect.MariaDBDialect`, so the
live answer is core's ``False``. The two disagree; see the report for that.
"""

from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.objects import SchemaObject

__all__ = ["MariaDBNamespaceMixin"]


class MariaDBNamespaceMixin:
    """MariaDB names are qualified by database and by nothing else.

    Listed ahead of core's ``NamespaceMixin`` in the dialect's base list,
    because that mixin supplies a default ``supports_catalog()`` of ``False``
    and plain mixins are resolved by position rather than by inheritance. A
    later entry would not override an earlier one; C3 would raise instead.
    """

    #: What goes between the levels of a qualified name. Stated here rather
    #: than inherited because it is a fact about MariaDB's grammar, and this
    #: is the only file in the backend where the answer is recorded. It
    #: happens to agree with core's default, so nothing depends on the
    #: difference; agreeing by accident is what made the shape worth writing
    #: down.
    separator: str = "."

    def format_qualified_name(self, expr: "SchemaObject") -> Tuple[str, tuple]:
        """Spell *expr*'s name as ``database`.`name``.

        One level, because MariaDB has one. A name carrying no database comes
        out bare, which is the common case: MariaDB resolves an unqualified
        name against the connection's own database.

        Call
        :meth:`~rhosocial.activerecord.backend.dialect.mixins.schema_namespace.NamespaceMixin.validate_namespace`
        first. It is what refuses a ``schema_name``, so by the time this runs
        there is at most one level to join.

        Args:
            expr: The object being named.

        Returns:
            A ``(sql, params)`` tuple. ``params`` is empty because an
            identifier is never a bind parameter.
        """
        parts: List[str] = []
        if expr.catalog_name:
            parts.append(
                self.format_identifier(expr.catalog_name, expr.catalog_need_quote)
            )
        parts.append(self.format_identifier(expr.name, expr.name_need_quote))
        return self.separator.join(parts), ()

    def supports_catalog(self) -> bool:
        """Whether MariaDB models a namespace above the (absent) schema.

        The slot above a name is a database in MariaDB. It is called a catalog
        because that is the slot's name in the object tree, not because MariaDB
        has SQL-standard catalogs.
        """
        return True

    def supports_catalog_qualification(self) -> bool:
        """Whether the database is rendered when a name carries one.

        ``app`.`users`` addresses another database outright, so yes.
        """
        return True
