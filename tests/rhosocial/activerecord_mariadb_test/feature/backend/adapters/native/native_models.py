# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/native_models.py
"""Models over MariaDB's native column types, and their table definitions.

One model per table so a failure names the family (see the testing plan
§4.1). The column types are MariaDB's own: ``BIT``/``SET``/``ENUM``/``YEAR``/
``JSON``/``UUID``/``GEOMETRY`` cannot be expressed through the shared neutral
fixtures.

Declared adapters are the point of these models: the *target* type decides the
wire form (``BIT`` as ``int`` because a padded byte can be wider than the
column; ``UUID`` as text or the 16 raw bytes; ``SET`` as the sorted text the
server accepts).

The tables themselves are declared by the definition classes at the end of
this module: each one receives only a ``dialect`` and builds its DDL from
MariaDB's expression type classes, so what runs against a server is decided
by the L2 fixtures, never by the model.
"""
from rhosocial.activerecord.backend.suggestion import IntegerAutoIncrementSuggestionRenderer  # noqa: E402

from enum import Enum
from typing import Optional, Set
from uuid import UUID

from pydantic import ConfigDict

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.base.fields import UseAdapter
from rhosocial.activerecord.backend.adapters import BitString, Geometry, Point
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint as Constraint,
    ColumnDefinition as Column,
    CreateTableStatement as CreateTable,
    DropTableStatement as DropTable,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint as PrimaryKey,
)
from rhosocial.activerecord.backend.expression.types import (
    CharType as Char,
    IntegerType as Int,
    JsonType as Json,
)
from rhosocial.activerecord.backend.impl.mariadb.adapters import (
    MariaDBBitStringAdapter,
    MariaDBEnumAdapter,
    MariaDBJSONAdapter,
    MariaDBSetAdapter,
    MariaDBUUIDAdapter,
)
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBBitType,
    MariaDBEnumType,
    MariaDBGeometryType,
    MariaDBPointType,
    MariaDBSetType,
    MariaDBUUIDType,
    MariaDBYearType,
)
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.feature.query.fixtures.definitions import (
    supports_drop_if_exists,
)


class NativeBitRow(IntegerPKMixin, ActiveRecord):
    """``BIT(8)`` (byte aligned), ``BIT(5)`` and ``BIT(10)`` (not aligned)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_bit"

    id: Optional[int] = None
    flags8: Annotated[
        Optional[BitString], UseAdapter(MariaDBBitStringAdapter(bit_length=8), int)
    ] = None
    flags5: Annotated[
        Optional[BitString], UseAdapter(MariaDBBitStringAdapter(bit_length=5), int)
    ] = None
    flags10: Annotated[
        Optional[BitString], UseAdapter(MariaDBBitStringAdapter(bit_length=10), int)
    ] = None


class NativeSetRow(IntegerPKMixin, ActiveRecord):
    """``SET('a','b','c')`` carried as the sorted comma-separated text."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_set"

    id: Optional[int] = None
    tags: Annotated[
        Optional[Set[str]],
        UseAdapter(MariaDBSetAdapter(allowed_values=["a", "b", "c"]), str),
    ] = None


class Priority(str, Enum):
    """Names differ from values, so the stored label proves ``.value`` is used."""

    LOW = "p1"
    HIGH = "p2"


class NativeEnumRow(IntegerPKMixin, ActiveRecord):
    """``ENUM('p1','p2')``; the database label is the enum member's value."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_enum"

    id: Optional[int] = None
    color: Annotated[Optional[Priority], UseAdapter(MariaDBEnumAdapter(), str)] = None


class NativeYearRow(IntegerPKMixin, ActiveRecord):
    """``YEAR`` stays an ``int``: it is never reinterpreted as a date."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_year"

    id: Optional[int] = None
    yr: Optional[int] = None


class NativeJsonRow(IntegerPKMixin, ActiveRecord):
    """``JSON`` is MariaDB's ``LONGTEXT`` alias; the adapter speaks JSON text."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_json"

    id: Optional[int] = None
    payload: Annotated[Optional[dict], UseAdapter(MariaDBJSONAdapter(), str)] = None


class NativeUUIDRow(IntegerPKMixin, ActiveRecord):
    """The native ``UUID`` column and the ``CHAR(36)`` carrier side by side."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_uuid"

    id: Optional[int] = None
    uid_native: Annotated[Optional[UUID], UseAdapter(MariaDBUUIDAdapter(), str)] = None
    uid_carrier: Annotated[Optional[UUID], UseAdapter(MariaDBUUIDAdapter(), str)] = None
    uid_bytes: Annotated[Optional[UUID], UseAdapter(MariaDBUUIDAdapter(), bytes)] = None


class NativeGeometryRow(IntegerPKMixin, ActiveRecord):
    """Geometry columns read back as the server's binary form.

    Plain WKT parameter binding is rejected by the server (errno 1416), so this
    model exists to pin that rejection; the passing checks read ``ST_AsText``
    through native SQL instead.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def table_name(cls) -> str:
        return "native_geometry"

    id: Optional[int] = None
    geom: Optional[Geometry] = None
    pt: Optional[Point] = None
    srid_geom: Optional[Geometry] = None


# --- L1 fixture definitions ---------------------------------------------------
# A definition class receives only a ``dialect``: it holds the DDL its table
# needs and knows nothing about backends, databases, or execution.  Which
# statements run, and when, is decided by the L2 fixtures in the directory.
#
# MariaDB's native families (``BIT``, ``SET``, ``ENUM``, ``YEAR``, a ``JSON``
# document, the native ``UUID`` type, and the spatial family with its
# ``REF_SYSTEM_ID`` attribute) each have their own type class in
# ``rhosocial.activerecord.backend.impl.mariadb.expression``, so the tables are
# built from those classes rather than from raw SQL.


class Definition:
    """Base class for this directory's table definitions."""

    model = None
    table_name = ""

    def __init__(self, dialect):
        self.dialect = dialect
        self.name = type(self).table_name
        self.create_table = CreateTable(
            self.dialect,
            table=Table(self.dialect, self.name),
            columns=self.columns(),
        )
        self.drop_table = DropTable(
            self.dialect,
            table=Table(self.dialect, self.name),
            if_exists=supports_drop_if_exists(self.dialect),
        )

    def columns(self):
        raise NotImplementedError

    def column(self, name, sql_type, constraints=None):
        return Column(self.dialect, name, sql_type, constraints=constraints or [])

    def auto_pk(self, name="id"):
        data_type, attributes = IntegerAutoIncrementSuggestionRenderer().parts(self.dialect, Int(self.dialect))
        return Column(
            self.dialect,
            name,
            data_type,
            constraints=[Constraint(self.dialect, branch=PrimaryKey(self.dialect))],
            attributes=attributes,
        )



class NativeBitDefinition(Definition):
    """``BIT(8)``, ``BIT(5)`` and ``BIT(10)``."""

    model = NativeBitRow
    table_name = "native_bit"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("flags8", MariaDBBitType(self.dialect, 8)),
            self.column("flags5", MariaDBBitType(self.dialect, 5)),
            self.column("flags10", MariaDBBitType(self.dialect, 10)),
        ]


class NativeSetDefinition(Definition):
    """``SET('a','b','c')``."""

    model = NativeSetRow
    table_name = "native_set"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("tags", MariaDBSetType(self.dialect, ["a", "b", "c"])),
        ]


class NativeEnumDefinition(Definition):
    """``ENUM('p1','p2')``."""

    model = NativeEnumRow
    table_name = "native_enum"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("color", MariaDBEnumType(self.dialect, ["p1", "p2"])),
        ]


class NativeYearDefinition(Definition):
    """``YEAR``."""

    model = NativeYearRow
    table_name = "native_year"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("yr", MariaDBYearType(self.dialect)),
        ]


class NativeJsonDefinition(Definition):
    """A ``JSON`` column (MariaDB stores it as ``LONGTEXT``)."""

    model = NativeJsonRow
    table_name = "native_json"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("payload", Json(self.dialect)),
        ]


class NativeGeometryDefinition(Definition):
    """A generic ``GEOMETRY``, a ``POINT`` and an SRID-declared ``GEOMETRY``."""

    model = NativeGeometryRow
    table_name = "native_geometry"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("geom", MariaDBGeometryType(self.dialect)),
            self.column("pt", MariaDBPointType(self.dialect)),
            self.column("srid_geom", MariaDBGeometryType(self.dialect, srid=4326)),
        ]


class NativeUuidDefinition(Definition):
    """The native ``UUID`` type beside its ``CHAR(36)`` carrier.

    ``UUID`` is a real column type since MariaDB 10.7; on an older server this
    table does not exist (see ``native_capabilities``).
    """

    model = NativeUUIDRow
    table_name = "native_uuid"

    def columns(self):
        return [
            self.auto_pk(),
            self.column("uid_native", MariaDBUUIDType(self.dialect)),
            self.column("uid_carrier", Char(self.dialect, 36)),
            self.column("uid_bytes", MariaDBUUIDType(self.dialect)),
        ]
