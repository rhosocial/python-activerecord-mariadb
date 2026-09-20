# src/rhosocial/activerecord/backend/impl/mariadb/protocols/charset.py
"""MariaDB charset / collation / storage-engine support protocol."""

from typing import FrozenSet, Optional, Protocol, runtime_checkable


@runtime_checkable
class MariaDBCharsetCollationSupport(Protocol):
    """Version-aware MariaDB charset / collation / storage-engine support.

    Implementations expose the values available on the configured server
    version and validate user input against that whitelist.
    """

    def supported_charsets(self) -> FrozenSet[str]:
        """Character sets available on the configured server version."""
        ...

    def supports_charset(self, name: object) -> bool:
        """Whether ``name`` is a known charset (version-gated)."""
        ...

    def validate_charset_name(self, name: object) -> str:
        """Return the normalized charset name or raise ``ValueError``."""
        ...

    def supported_collations(self, charset: Optional[str] = None) -> FrozenSet[str]:
        """Collations available on the configured server version."""
        ...

    def supports_collation_name(self, name: str) -> bool:
        """Whether ``name`` is a known collation (version-gated)."""
        ...

    def validate_collation_by_name(self, name: str) -> str:
        """Return the normalized collation name or raise ``ValueError``."""
        ...

    def supported_storage_engines(self) -> FrozenSet[str]:
        """Storage engines available on the configured server version."""
        ...

    def supports_storage_engine(self, name: object) -> bool:
        """Whether ``name`` is a known storage engine (version-gated)."""
        ...

    def validate_storage_engine_name(self, name: object) -> str:
        """Return the canonical storage engine name or raise ``ValueError``."""
        ...
