# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/create_table_layout_suggestion.py
"""MariaDB's CREATE TABLE layout suggestion.

MariaDB inlines both INDEX/KEY definitions and the table COMMENT in a single
CREATE TABLE statement. The answer is assembled from the dialect's own
capability probes rather than hardcoded, so a dialect that withdraws either
capability automatically falls back to the split layout.
"""

from rhosocial.activerecord.backend.suggestion.definitions import CreateTableLayoutSuggestion


class MariaDBCreateTableLayoutSuggestionMixin:
    """Report the inline CREATE TABLE layout MariaDB can render.

    Deliberately a plain class, not a subclass of the runtime-checkable
    ``CreateTableLayoutSuggestionSupport`` Protocol: placing a Protocol in the
    dialect MRO ahead of ``SQLDialectBase`` swallows ``super().__init__()`` and
    leaves ``strict_validation`` unset (see the same caveat in
    ``string_concatenation_suggestion.py``). Duck typing satisfies the
    ``isinstance`` protocol check without polluting the MRO.
    """

    def suggest_create_table_layout(self) -> CreateTableLayoutSuggestion:
        inline_index = bool(self.supports_inline_index())
        inline_comment = bool(self.supports_table_comment())
        return CreateTableLayoutSuggestion(
            strategy="single" if inline_index and inline_comment else "split",
            inline_index=inline_index,
            inline_comment=inline_comment,
            state="actions",
        )
