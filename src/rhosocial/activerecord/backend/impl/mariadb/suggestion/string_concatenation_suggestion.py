# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/string_concatenation_suggestion.py
"""MariaDB's string-concatenation spelling suggestion."""

from rhosocial.activerecord.backend.suggestion.definitions import ConcatenationFunctionSuggestion


class MariaDBStringConcatenationSuggestionMixin:
    """Answer core's ``StringConcatenationSuggestionSupport`` protocol.

    MariaDB spells concatenation with ``CONCAT(a, b)``. ``||`` is logical OR
    unless the server runs with ``PIPES_AS_CONCAT``, so the function is the only
    unconditional spelling. ``MariaDBFunctionMixin.STRING_CONCATENATION`` carries
    the same answer for the function-capability side; this mixin answers the
    suggestion protocol core's ``format_concatenation_operation`` consults.

    Deliberately a plain class, not a subclass of the runtime-checkable Protocol:
    that would insert a Protocol into the dialect MRO ahead of ``SQLDialectBase``
    and swallow ``super().__init__()`` (which sets ``strict_validation``).
    """

    def suggest_concatenation_function(self):
        declared = getattr(self, "STRING_CONCATENATION", None)
        return ConcatenationFunctionSuggestion(
            function=declared if isinstance(declared, str) else None
        )
