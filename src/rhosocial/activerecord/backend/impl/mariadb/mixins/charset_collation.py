# src/rhosocial/activerecord/backend/impl/mariadb/mixins/charset_collation.py
"""MariaDB charset / collation / storage-engine dialect support.

Implements :class:`~...mariadb.protocols.MariaDBCharsetCollationSupport`: a
version-aware whitelist of character sets, collations and storage engines,
plus the ``validate_*`` interface used by table/column expressions at
construction time.

The whitelists and their version gates are implementation details of this
dialect mixin; callers go through the dialect methods.
"""

from enum import Enum
from typing import FrozenSet, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.collation import CollateExpression

__all__ = [
    "MariaDBCharset",
    "MariaDBStorageEngine",
    "MariaDBCollation",
    "MariaDBCharsetCollationMixin",
]


class MariaDBCharset(Enum):
    """MariaDB character sets for table/column ``CHARACTER SET``."""

    ARMSCII8 = "armscii8"
    ASCII = "ascii"
    BIG5 = "big5"
    BINARY = "binary"
    CP1250 = "cp1250"
    CP1251 = "cp1251"
    CP1256 = "cp1256"
    CP1257 = "cp1257"
    CP850 = "cp850"
    CP852 = "cp852"
    CP866 = "cp866"
    CP932 = "cp932"
    DEC8 = "dec8"
    EUCJPMS = "eucjpms"
    EUCKR = "euckr"
    GB18030 = "gb18030"
    GB2312 = "gb2312"
    GBK = "gbk"
    GEOSTD8 = "geostd8"
    GREEK = "greek"
    HEBREW = "hebrew"
    HP8 = "hp8"
    KEYBCS2 = "keybcs2"
    KOI8R = "koi8r"
    KOI8U = "koi8u"
    LATIN1 = "latin1"
    LATIN2 = "latin2"
    LATIN5 = "latin5"
    LATIN7 = "latin7"
    MACCE = "macce"
    MACROMAN = "macroman"
    SJIS = "sjis"
    SWE7 = "swe7"
    TIS620 = "tis620"
    UCS2 = "ucs2"
    UJIS = "ujis"
    UTF8 = "utf8"
    UTF8MB3 = "utf8mb3"
    UTF8MB4 = "utf8mb4"
    UTF16 = "utf16"
    UTF16LE = "utf16le"
    UTF32 = "utf32"


class MariaDBStorageEngine(Enum):
    """Built-in MariaDB storage engines for ``ENGINE=<name>``."""

    INNODB = "InnoDB"
    MYISAM = "MyISAM"
    ARIA = "Aria"
    MEMORY = "MEMORY"
    CSV = "CSV"
    ARCHIVE = "ARCHIVE"
    BLACKHOLE = "BLACKHOLE"
    MRG_MYISAM = "MRG_MyISAM"
    SEQUENCE = "SEQUENCE"
    CONNECT = "CONNECT"
    FEDERATED = "FEDERATED"
    PERFORMANCE_SCHEMA = "PERFORMANCE_SCHEMA"


class MariaDBCollation(Enum):
    """Common MariaDB collations for expression-level COLLATE."""

    BINARY = "binary"
    LATIN1_SWEDISH_CI = "latin1_swedish_ci"
    UTF8_GENERAL_CI = "utf8_general_ci"
    UTF8_UNICODE_CI = "utf8_unicode_ci"
    UTF8MB4_BIN = "utf8mb4_bin"
    UTF8MB4_GENERAL_CI = "utf8mb4_general_ci"
    UTF8MB4_UNICODE_CI = "utf8mb4_unicode_ci"


_CHARSET_BY_VALUE = {member.value: member for member in MariaDBCharset}
_ENGINE_BY_LOWER = {member.value.lower(): member for member in MariaDBStorageEngine}
_COLLATION_VALUES = {member.value for member in MariaDBCollation}

# Introduced-in server versions for version-gated values.
_CHARSET_MIN_VERSIONS: dict = {
    "utf8mb4": (5, 5, 3),
    "utf8mb3": (10, 6, 0),
}
_ENGINE_MIN_VERSIONS: dict = {
    "SEQUENCE": (10, 3, 0),
}
_COLLATION_MIN_VERSIONS: dict = {}


class MariaDBCharsetCollationMixin:
    """Version-aware charset / collation / storage-engine dialect support."""

    def _mariadb_capability_version(self) -> Optional[Tuple[int, ...]]:
        # Read the private attribute: the public ``version`` property raises
        # ``DialectNotAdaptedException`` when no version was supplied, but
        # validation only needs the version *if* it is known.
        return getattr(self, "_version", None)

    # --- expression-level COLLATE ---------------------------------------
    def supports_collate_expression(self) -> bool:
        """MariaDB supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a ``CollateExpression`` and return its collation SQL."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        return self.validate_collation_by_name(expr.collation_name)

    # --- charset ---------------------------------------------------------
    def supported_charsets(self) -> FrozenSet[str]:
        """Charset names available on the configured server version."""
        version = self._mariadb_capability_version()
        return frozenset(
            member.value
            for member in MariaDBCharset
            if version is None
            or _CHARSET_MIN_VERSIONS.get(member.value) is None
            or version >= _CHARSET_MIN_VERSIONS[member.value]
        )

    def supports_charset(self, name: object) -> bool:
        try:
            self.validate_charset_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_charset_name(self, name: object) -> str:
        version = self._mariadb_capability_version()
        if isinstance(name, MariaDBCharset):
            normalized = name.value
        elif isinstance(name, str):
            normalized = name.lower()
        else:
            raise TypeError(
                f"character set must be MariaDBCharset or str, got {type(name).__name__}"
            )
        if normalized not in _CHARSET_BY_VALUE:
            raise ValueError(f"Unsupported MariaDB character set: {name!r}")
        min_version = _CHARSET_MIN_VERSIONS.get(normalized)
        if version is not None and min_version is not None and version < min_version:
            formatted = ".".join(str(part) for part in min_version[:2])
            raise ValueError(f"MariaDB character set requires MariaDB {formatted}+: {name!r}")
        return normalized

    # --- collation -------------------------------------------------------
    def supported_collations(self, charset: Optional[str] = None) -> FrozenSet[str]:
        """Collation names available on the configured server version."""
        version = self._mariadb_capability_version()
        names = set()
        for name in _COLLATION_VALUES:
            min_version = _COLLATION_MIN_VERSIONS.get(name)
            if version is not None and min_version is not None and version < min_version:
                continue
            if charset is not None:
                prefix = charset.lower() + "_"
                if not (
                    name.startswith(prefix)
                    or (charset.lower() == "binary" and name == "binary")
                ):
                    continue
            names.add(name)
        return frozenset(names)

    def supports_collation_name(self, name: str) -> bool:
        try:
            self.validate_collation_by_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_collation_by_name(self, name: str) -> str:
        version = self._mariadb_capability_version()
        if not isinstance(name, str):
            raise TypeError(f"collation must be str, got {type(name).__name__}")
        normalized = name.lower()
        if normalized not in _COLLATION_VALUES:
            raise ValueError(f"Unsupported MariaDB collation: {name!r}")
        min_version = _COLLATION_MIN_VERSIONS.get(normalized)
        if version is not None and min_version is not None and version < min_version:
            formatted = ".".join(str(part) for part in min_version[:2])
            raise ValueError(f"MariaDB collation requires MariaDB {formatted}+: {name!r}")
        return normalized

    # --- storage engine --------------------------------------------------
    def supported_storage_engines(self) -> FrozenSet[str]:
        """Storage engine names available on the configured server version."""
        version = self._mariadb_capability_version()
        return frozenset(
            member.value
            for member in MariaDBStorageEngine
            if version is None
            or _ENGINE_MIN_VERSIONS.get(member.value) is None
            or version >= _ENGINE_MIN_VERSIONS[member.value]
        )

    def supports_storage_engine(self, name: object) -> bool:
        try:
            self.validate_storage_engine_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_storage_engine_name(self, name: object) -> str:
        version = self._mariadb_capability_version()
        if isinstance(name, MariaDBStorageEngine):
            canonical = name.value
        elif isinstance(name, str):
            member = _ENGINE_BY_LOWER.get(name.lower())
            if member is None:
                raise ValueError(f"Unsupported MariaDB storage engine: {name!r}")
            canonical = member.value
        else:
            raise TypeError(
                f"storage engine must be MariaDBStorageEngine or str, "
                f"got {type(name).__name__}"
            )
        min_version = _ENGINE_MIN_VERSIONS.get(canonical)
        if version is not None and min_version is not None and version < min_version:
            formatted = ".".join(str(part) for part in min_version[:2])
            raise ValueError(f"MariaDB storage engine requires MariaDB {formatted}+: {name!r}")
        return canonical
