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
    # ``utf8`` is a server-side *alias* whose meaning changed in MariaDB
    # 13.1 (MDEV-30041): it resolved to ``utf8mb3`` on every release up to
    # 13.0 and resolves to ``utf8mb4`` from 13.1, because ``old_mode`` no
    # longer sets ``UTF8_IS_UTF8MB3`` by default. Emitting a bare ``utf8``
    # therefore produces a *different column charset* depending on the
    # server version, so ``validate_charset_name`` resolves it to
    # ``utf8mb3`` -- the meaning it always had before 13.1 -- and the same
    # DDL yields the same schema on every supported server.
    # Prefer ``UTF8MB4`` (or ``UTF8MB3``) to be explicit.
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
    # 3-byte family. MariaDB 10.6 renamed these to the explicit utf8mb3_*
    # spellings and dropped the old names; see _COLLATION_VERSIONS.
    UTF8_GENERAL_CI = "utf8_general_ci"
    UTF8_UNICODE_CI = "utf8_unicode_ci"
    UTF8MB3_GENERAL_CI = "utf8mb3_general_ci"
    UTF8MB3_UNICODE_CI = "utf8mb3_unicode_ci"
    UTF8MB4_BIN = "utf8mb4_bin"
    UTF8MB4_GENERAL_CI = "utf8mb4_general_ci"
    UTF8MB4_UNICODE_CI = "utf8mb4_unicode_ci"


_CHARSET_BY_VALUE = {member.value: member for member in MariaDBCharset}
_ENGINE_BY_LOWER = {member.value.lower(): member for member in MariaDBStorageEngine}
_COLLATION_VALUES = {member.value for member in MariaDBCollation}

# Introduced-in server versions for version-gated character sets.
_CHARSET_MIN_VERSIONS: dict = {
    # MariaDB 5.5.3 is a real MariaDB release and is where utf8mb4 landed,
    # so this threshold is meaningful for a backend that supports 10.2+.
    "utf8mb4": (5, 5, 3),
    "utf8mb3": (10, 6, 0),
    "utf8": (10, 0, 0),
}

# Availability windows for version-gated collations, as
# ``name -> (min_version, max_version)``. A ``None`` bound means unbounded.
#
# Verified against live servers: MariaDB 10.6 renamed the 3-byte family from
# ``utf8_*`` to the explicit ``utf8mb3_*`` and dropped the old spellings, so
# these are *removals* at 10.6 rather than additions. The ``utf8mb4_*``
# collations predate every release this backend supports.
_COLLATION_VERSIONS: dict = {
    "utf8_general_ci": (None, (10, 5, 0)),
    "utf8_unicode_ci": (None, (10, 5, 0)),
    "utf8mb3_general_ci": ((10, 6, 0), None),
    "utf8mb3_unicode_ci": ((10, 6, 0), None),
    "utf8mb4_bin": ((5, 5, 3), None),
    "utf8mb4_general_ci": ((5, 5, 3), None),
    "utf8mb4_unicode_ci": ((5, 5, 3), None),
}
_ENGINE_MIN_VERSIONS: dict = {
    "SEQUENCE": (10, 3, 0),
}

#: Charsets that are ambiguous server-side aliases, mapped to the explicit
#: spelling they should be emitted as, together with the minimum server
#: version at which that spelling is valid.
#:
#: The point of resolving them is that generated DDL is *identical* on every
#: supported server version. ``utf8`` is the only such alias: it meant
#: ``utf8mb3`` on every MariaDB release up to 13.0, then became an alias for
#: ``utf8mb4`` in 13.1 (MDEV-30041 dropped the default
#: ``old_mode=UTF8_IS_UTF8MB3`` flag). Passing ``utf8`` through therefore
#: makes the column charset depend on the server version.
#:
#: It resolves to ``utf8mb3`` -- the historical meaning -- rather than to
#: ``utf8mb4``. Resolving forward instead would silently widen the column on
#: every pre-13.1 server, trading one silent drift for another. Callers who
#: want 4-byte storage must ask for ``utf8mb4`` explicitly.
#:
#: Below MariaDB 10.6 the explicit ``utf8mb3`` name is not documented, so the
#: alias is passed through unchanged there. That is still unambiguous: on
#: every version before 13.1 ``utf8`` can only mean ``utf8mb3``.
_CHARSET_ALIASES: dict = {
    "utf8": ((10, 6, 0), "utf8mb3"),
}


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
        """Charset names available on the configured server version.

        An alias is reported under the explicit spelling it resolves to, so
        the returned set never contains a name whose meaning depends on the
        server version. Where the explicit spelling is not yet valid the alias
        itself is reported, since it is unambiguous at that point.
        """
        version = self._mariadb_capability_version()
        names = set()
        for member in MariaDBCharset:
            if version is not None:
                min_version = _CHARSET_MIN_VERSIONS.get(member.value)
                if min_version is not None and version < min_version:
                    continue
            names.add(self._resolve_charset_alias(member.value, version))
        return frozenset(names)

    @staticmethod
    def _resolve_charset_alias(
        name: str, version: Optional[Tuple[int, ...]] = None
    ) -> str:
        """Map an ambiguous charset alias to the spelling to emit.

        Falls back to the alias itself when the server predates the explicit
        spelling, or when the version is unknown.
        """
        entry = _CHARSET_ALIASES.get(name)
        if entry is None:
            return name
        valid_from, replacement = entry
        if version is None or version < valid_from:
            return name
        return replacement

    def supports_charset(self, name: object) -> bool:
        try:
            self.validate_charset_name(name)
        except (TypeError, ValueError):
            return False
        return True

    def validate_charset_name(self, name: object) -> str:
        """Validate a charset and return the spelling to emit in SQL.

        The ambiguous alias ``utf8`` is resolved to ``utf8mb3`` from MariaDB
        10.6, which is what it meant on every release before 13.1. Emitting
        the alias itself on 13.1+ would make the resulting column charset
        depend on the server version; resolving it means one DDL statement
        produces one schema on every supported server. Ask for ``utf8mb4`` to
        get 4-byte storage.
        """
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
        return self._resolve_charset_alias(normalized, version)

    # --- collation -------------------------------------------------------
    def supported_collations(self, charset: Optional[str] = None) -> FrozenSet[str]:
        """Collation names available on the configured server version."""
        version = self._mariadb_capability_version()
        names = set()
        for name in _COLLATION_VALUES:
            window = _COLLATION_VERSIONS.get(name)
            if version is not None and window is not None:
                min_version, max_version = window
                if min_version is not None and version < min_version:
                    continue
                if max_version is not None and version > max_version:
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
        window = _COLLATION_VERSIONS.get(normalized)
        if version is not None and window is not None:
            min_version, max_version = window
            if min_version is not None and version < min_version:
                formatted = ".".join(str(part) for part in min_version[:2])
                raise ValueError(
                    f"MariaDB collation requires MariaDB {formatted}+: {name!r}"
                )
            if max_version is not None and version > max_version:
                last = ".".join(str(part) for part in max_version[:2])
                raise ValueError(
                    f"MariaDB collation is not available after MariaDB {last}: "
                    f"use the utf8mb3_* spelling instead ({name!r})"
                )
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
