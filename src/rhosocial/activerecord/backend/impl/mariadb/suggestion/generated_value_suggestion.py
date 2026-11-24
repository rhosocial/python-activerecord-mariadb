# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/generated_value_suggestion.py
"""MariaDB's database-generated-value suggestion.

The answer is the backend's own spelling, assembled from its capability
probes where it has one. It is placed first in the dialect bases so no core
mixin can shadow it, and it renders nothing itself -- the returned clause's
formatter owns the SQL spelling.

Deliberately a plain class, not a subclass of the runtime-checkable
``GeneratedValueSuggestionSupport`` Protocol: that would insert a Protocol
into the dialect MRO ahead of ``SQLDialectBase`` and swallow
``super().__init__()`` (which sets ``strict_validation``). Duck typing
satisfies the ``isinstance`` check without polluting the MRO.
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.suggestion import GeneratedValueSuggestion

from ....expression.statements import AutoIncrementClause

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types._base import DataType


class MariaDBGeneratedValueSuggestionMixin:
    """Suggest mariadb's declaration for a generated integer key."""

    def suggest_generated_value(self, default_type: "DataType") -> GeneratedValueSuggestion:
        if not self.supports_auto_increment_column():
            from ....dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(
                self.name,
                "AUTO_INCREMENT column",
                "This dialect has withdrawn support for the AUTO_INCREMENT marker.",
            )
        return GeneratedValueSuggestion(
            state="generate",
            storage_type=default_type,
            clause=AutoIncrementClause(self),
        )
