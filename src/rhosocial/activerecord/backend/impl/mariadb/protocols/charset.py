# src/rhosocial/activerecord/backend/impl/mariadb/protocols/charset.py
"""MariaDB charset / collation / storage-engine support protocol."""

from typing import FrozenSet, Optional, Protocol, runtime_checkable


@runtime_checkable
class MariaDBCharsetCollationSupport(Protocol):
    """Version-aware MariaDB charset / collation / storage-engine support.

    Implementations expose the values available on the configured server
    version and validate user input against that whitelist. Naming is a
    format-time validation (``validate_*``), not a capability flag: the
    ``supports_*`` methods here are the per-engine switches, whose only input
    is the dialect configuration.
    """

    def supported_charsets(self) -> FrozenSet[str]:
        """Character sets available on the configured server version."""
        ...

    def validate_charset_name(self, name: object) -> str:
        """Return the normalized charset name or raise ``ValueError``."""
        ...

    def supported_collations(self, charset: Optional[str] = None) -> FrozenSet[str]:
        """Collations available on the configured server version."""
        ...

    def validate_collation_by_name(self, name: str) -> str:
        """Return the normalized collation name or raise ``ValueError``."""
        ...

    def supported_storage_engines(self) -> FrozenSet[str]:
        """Storage engines available on the configured server version."""
        ...

    def validate_storage_engine_name(self, name: object) -> str:
        """Return the canonical storage engine name or raise ``ValueError``."""
        ...

    def supports_storage_engine_innodb(self) -> bool:
        """Whether ``ENGINE=InnoDB`` is available."""
        ...

    def supports_storage_engine_myisam(self) -> bool:
        """Whether ``ENGINE=MyISAM`` is available."""
        ...

    def supports_storage_engine_aria(self) -> bool:
        """Whether ``ENGINE=Aria`` is available."""
        ...

    def supports_storage_engine_memory(self) -> bool:
        """Whether ``ENGINE=MEMORY`` is available."""
        ...

    def supports_storage_engine_csv(self) -> bool:
        """Whether ``ENGINE=CSV`` is available."""
        ...

    def supports_storage_engine_archive(self) -> bool:
        """Whether ``ENGINE=ARCHIVE`` is available."""
        ...

    def supports_storage_engine_blackhole(self) -> bool:
        """Whether ``ENGINE=BLACKHOLE`` is available."""
        ...

    def supports_storage_engine_mrg_myisam(self) -> bool:
        """Whether ``ENGINE=MRG_MyISAM`` is available."""
        ...

    def supports_storage_engine_sequence(self) -> bool:
        """Whether ``ENGINE=SEQUENCE`` is available (MariaDB 10.3+)."""
        ...

    def supports_storage_engine_connect(self) -> bool:
        """Whether ``ENGINE=CONNECT`` is available."""
        ...

    def supports_storage_engine_federated(self) -> bool:
        """Whether ``ENGINE=FEDERATED`` is available."""
        ...

    def supports_storage_engine_performance_schema(self) -> bool:
        """Whether ``ENGINE=PERFORMANCE_SCHEMA`` is available."""
        ...

    def supports_storage_engine_ndb(self) -> bool:
        """Whether ``ENGINE=NDB`` is available."""
        ...

    def supports_storage_engine_ndbcluster(self) -> bool:
        """Whether ``ENGINE=NDBCLUSTER`` is available."""
        ...

    def supports_storage_engine_example(self) -> bool:
        """Whether ``ENGINE=EXAMPLE`` is available."""
        ...

    def supports_storage_engine_temporary(self) -> bool:
        """Whether ``ENGINE=TEMPORARY`` is available."""
        ...
