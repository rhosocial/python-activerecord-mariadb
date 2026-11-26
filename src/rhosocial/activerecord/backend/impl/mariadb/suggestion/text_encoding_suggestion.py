# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/text_encoding_suggestion.py
"""MariaDB's text-encoding suggestion."""

from rhosocial.activerecord.backend.suggestion.definitions import TextEncodingSuggestion


class MariaDBTextEncodingSuggestionMixin:
    """Answer core's ``TextEncodingSuggestionSupport`` protocol.

    ``utf8mb4`` is MariaDB's 4-byte Unicode character set and the one an
    ordinary table should carry: ``utf8mb3``/``utf8`` cannot store emoji or
    supplementary-plane text. ``utf8mb4_general_ci`` is the collation the
    server pairs with ``utf8mb4`` by default, so naming it keeps the DDL
    identical on every supported release instead of inheriting whatever the
    server's ``collation_server`` happens to be.

    The pair is passed through this dialect's own validation, so a future
    version gate that removes either name makes this answer fail loudly here
    rather than render an unsupported DDL elsewhere.

    Deliberately a plain class, not a subclass of the runtime-checkable
    protocol: that would put a Protocol into the dialect MRO ahead of
    ``SQLDialectBase`` and swallow ``super().__init__()``.
    """

    def suggest_text_encoding(self) -> TextEncodingSuggestion:
        """Return the charset/collation MariaDB recommends."""
        return TextEncodingSuggestion(
            charset=self.validate_charset_name("utf8mb4"),
            collation=self.validate_collation_by_name("utf8mb4_general_ci"),
            reason=(
                "utf8mb4 stores all Unicode including 4-byte characters; "
                "utf8mb4_general_ci is MariaDB's default collation for it."
            ),
        )
