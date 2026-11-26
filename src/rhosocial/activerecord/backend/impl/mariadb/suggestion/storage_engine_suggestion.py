# src/rhosocial/activerecord/backend/impl/mariadb/suggestion/storage_engine_suggestion.py
"""MariaDB's storage-engine suggestion."""

from rhosocial.activerecord.backend.suggestion.definitions import StorageEngineSuggestion


class MariaDBStorageEngineSuggestionMixin:
    """Answer core's ``StorageEngineSuggestionSupport`` protocol.

    InnoDB is the only engine on MariaDB that gives an ordinary table
    transactions, row locks and foreign keys together, so it is the answer for
    a table the caller has not otherwise characterised. ``transactional=True``
    records that, and the engine word is passed through this dialect's own
    validation so the suggestion cannot name an engine the formatter refuses.

    Deliberately a plain class, not a subclass of the runtime-checkable
    protocol: that would put a Protocol into the dialect MRO ahead of
    ``SQLDialectBase`` and swallow ``super().__init__()``.
    """

    def suggest_storage_engine(self) -> StorageEngineSuggestion:
        """Return the storage engine MariaDB recommends."""
        return StorageEngineSuggestion(
            engine=self.validate_storage_engine_name("InnoDB"),
            transactional=True,
            reason=(
                "InnoDB provides transactions, row-level locking and foreign "
                "keys on every MariaDB release this backend targets."
            ),
        )
