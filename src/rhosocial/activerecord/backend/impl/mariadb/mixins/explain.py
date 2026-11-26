# src/rhosocial/activerecord/backend/impl/mariadb/mixins/explain.py
"""MariaDB EXPLAIN support mixin."""
from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBExplainMixin:
    """MariaDB EXPLAIN support.

    MariaDB's grammar admits ``EXPLAIN [ANALYZE] [FORMAT=JSON|TRADITIONAL]``
    from 10.6, and nothing else. Each support switch below answers one
    question about that grammar, so ``supports_explain_format_traditional``
    and ``supports_explain_format_tree`` are different answers rather than two
    spellings of one probe.
    """

    def supports_explain_analyze(self) -> bool:
        """EXPLAIN ANALYZE is supported since MariaDB 10.6."""
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT'])

    # --- formats ---------------------------------------------------------
    #: MariaDB spells the human-readable plan ``FORMAT=TRADITIONAL`` and the
    #: machine-readable one ``FORMAT=JSON``. There is no ``TEXT``, ``XML``,
    #: ``YAML`` or ``TREE`` keyword in its grammar -- measured against the
    #: wired servers, all four are rejected with errno 1064, and ``TREE`` is
    #: the MySQL 8.0 spelling this backend has never advertised.
    def supports_explain_format_text(self) -> bool:
        """MariaDB has no ``FORMAT=TEXT``."""
        return False

    def supports_explain_format_json(self) -> bool:
        """``FORMAT=JSON`` is supported since MariaDB 10.6."""
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT'])

    def supports_explain_format_xml(self) -> bool:
        """MariaDB has no ``FORMAT=XML``."""
        return False

    def supports_explain_format_yaml(self) -> bool:
        """MariaDB has no ``FORMAT=YAML``."""
        return False

    def supports_explain_format_tree(self) -> bool:
        """``FORMAT=TREE`` is MySQL 8.0 only; MariaDB never accepts it."""
        return False

    def supports_explain_format_traditional(self) -> bool:
        """``FORMAT=TRADITIONAL`` is supported since MariaDB 10.6."""
        return self.version_at_least(MARIADB_VERSION_BOUNDARIES['EXPLAIN_FORMAT'])

    # --- options ---------------------------------------------------------
    # MariaDB's plan-verbose spelling is ``EXPLAIN EXTENDED``; there is no
    # ``VERBOSE`` keyword, and no ``COSTS``, ``BUFFERS``, ``TIMING``,
    # ``SETTINGS`` or ``WAL`` keyword either. The switches answer False so
    # ``format_explain_statement`` refuses those requests instead of emitting
    # a statement the server cannot parse.
    def supports_explain_verbose(self) -> bool:
        """MariaDB spells this ``EXTENDED``; ``VERBOSE`` is not in its grammar."""
        return False

    def supports_explain_costs(self) -> bool:
        """MariaDB has no ``COSTS`` option."""
        return False

    def supports_explain_buffers(self) -> bool:
        """MariaDB has no ``BUFFERS`` option."""
        return False

    def supports_explain_timing(self) -> bool:
        """MariaDB has no ``TIMING`` option."""
        return False

    def supports_explain_settings(self) -> bool:
        """MariaDB has no ``SETTINGS`` option."""
        return False

    def supports_explain_wal(self) -> bool:
        """MariaDB has no ``WAL`` option."""
        return False


__all__ = ['MariaDBExplainMixin']
