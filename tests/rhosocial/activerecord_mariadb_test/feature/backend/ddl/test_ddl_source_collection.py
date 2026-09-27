# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_ddl_source_collection.py

try:
    from typing import Annotated, Optional
except ImportError:
    from typing_extensions import Annotated, Optional

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    GeneratedColumnExpression,
    GeneratedColumnType,
    IndexDefinition,
    StorageOptionsExpression,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression import (
    MariaDBColumnFormat,
    MariaDBColumnOptions,
    MariaDBColumnStorage,
    MariaDBCreateTableOptions,
    MariaDBIntType,
    MariaDBPartitionByRange,
    MariaDBTextType,
)
from rhosocial.activerecord.base import (
    CharacterSetAttribute,
    CollationAttribute,
    DDLAnnotation,
    DDLAnnotationHandler,
    DDLSource,
    IdentityAttribute,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseGeneratedColumn,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord


DIALECT = MariaDBDialect((11, 4, 0))
SQL_TYPE = MariaDBIntType(unsigned=True)
FALLBACK_SQL_TYPE = MariaDBTextType()
SQL_TYPE_MARKER = UseSqlType(SQL_TYPE, FALLBACK_SQL_TYPE)
DEFAULT_VALUE = Literal(DIALECT, "new", inline_literals=True)
DEFAULT_CONSTRAINT = UseConstraint(
    ColumnConstraintType.DEFAULT,
    name="df_status_default",
    default_value=DEFAULT_VALUE,
)
UNIQUE_CONSTRAINT = UseConstraint(
    ColumnConstraintType.UNIQUE,
    name="uq_status",
)
COLLATION = CollationAttribute(name="utf8mb4_general_ci")
CHARACTER_SET = CharacterSetAttribute(name="utf8mb4")
IDENTITY = IdentityAttribute(generation="ALWAYS", start=10, increment=2)
ATTRIBUTES = UseColumnAttributes(COLLATION, CHARACTER_SET, IDENTITY)
COMMENT = UseComment("current order status")
FIRST_INDEX = UseIndex(
    "idx_display_label",
    unique=True,
    type="BTREE",
    include_columns=["tenant_id"],
    if_not_exists=True,
    tablespace="innodb_index",
)
SECOND_INDEX = UseIndex("idx_display_label_suffix", type="BTREE")
GENERATED = GeneratedColumnExpression(
    DIALECT,
    Column(DIALECT, "order_id"),
    GeneratedColumnType.STORED,
)
COLUMN_OPTION = MariaDBColumnOptions(
    character_set="utf8mb4",
    column_format=MariaDBColumnFormat.FIXED,
    storage=MariaDBColumnStorage.MEMORY,
    invisible=True,
)
SECOND_COLUMN_OPTION = MariaDBColumnOptions(
    character_set="latin1",
    column_format=MariaDBColumnFormat.DYNAMIC,
    storage=MariaDBColumnStorage.DISK,
    invisible=False,
)
TABLE_CONSTRAINTS = [
    TableConstraint(
        DIALECT,
        TableConstraintType.FOREIGN_KEY,
        name="fk_order_tenant",
        columns=["tenant_id"],
        foreign_key_table="tenant",
        foreign_key_columns=["id"],
    ),
    TableConstraint(
        DIALECT,
        TableConstraintType.UNIQUE,
        name="uq_order_pair",
        columns=["tenant_id", "order_id"],
    ),
]
TABLE_INDEXES = [
    IndexDefinition(
        DIALECT,
        name="idx_table_status",
        columns=["status"],
        unique=True,
    ),
]
TABLE_OPTIONS = [
    MariaDBCreateTableOptions(
        DIALECT,
        engine="InnoDB",
        charset="utf8mb4",
        auto_increment=100,
    ),
]
STORAGE_OPTIONS = [
    StorageOptionsExpression(DIALECT, {"tablespace": "innodb_data_1"}),
]
TABLE_PARTITION = MariaDBPartitionByRange(
    DIALECT,
    [Column(DIALECT, "display_label")],
)
TABLE_INHERITS = ["order_audit_base"]
TABLE_TABLESPACE = "innodb_data_1"
MODEL_FIELDS = (
    "tenant_id",
    "order_id",
    "status",
    "label",
    "computed",
    "option_one",
    "option_many",
    "optional_note",
)
BATCH_METHODS = (
    "columns_name",
    "columns_type",
    "columns_constraints",
    "columns_attributes",
    "columns_indexes",
    "columns_comment",
    "columns_generated",
    "columns_options",
)


class BackendColumnOptionsAnnotation(DDLAnnotation):
    def __init__(self, *options):
        self.options = options


class BackendColumnOptionsHandler(DDLAnnotationHandler):
    annotation_types = (BackendColumnOptionsAnnotation,)

    @classmethod
    def apply(cls, new_class, field_name, annotation, metadata):
        metadata.add_column_options(*annotation.options)


class DDLDeclarations:
    __table_name__ = "ddl_source_orders"
    __primary_key__ = ("tenant_key", "order_key")
    __table_constraints__ = TABLE_CONSTRAINTS
    __table_indexes__ = TABLE_INDEXES
    _feature_handlers = [BackendColumnOptionsHandler]

    tenant_id: Annotated[
        int,
        UseColumn("tenant_key"),
        SQL_TYPE_MARKER,
    ]
    order_id: Annotated[int, UseColumn("order_key")]
    status: Annotated[
        str,
        DEFAULT_CONSTRAINT,
        UNIQUE_CONSTRAINT,
        ATTRIBUTES,
        COMMENT,
    ]
    label: Annotated[
        str,
        UseColumn("display_label"),
        FIRST_INDEX,
        SECOND_INDEX,
    ]
    computed: Annotated[int, UseGeneratedColumn(GENERATED)]
    option_one: Annotated[str, BackendColumnOptionsAnnotation(COLUMN_OPTION)]
    option_many: Annotated[
        str,
        BackendColumnOptionsAnnotation(COLUMN_OPTION, SECOND_COLUMN_OPTION),
    ]
    optional_note: Optional[str] = None

    @classmethod
    def table_options(cls):
        return TABLE_OPTIONS

    @classmethod
    def table_storage_options(cls):
        return STORAGE_OPTIONS

    @classmethod
    def table_partition(cls):
        return TABLE_PARTITION

    @classmethod
    def table_inherits(cls):
        return TABLE_INHERITS

    @classmethod
    def table_tablespace(cls):
        return TABLE_TABLESPACE


class SyncDDLSource(DDLDeclarations, ActiveRecord):
    pass


class AsyncDDLSource(DDLDeclarations, AsyncActiveRecord):
    pass


SINGLE_SQL_TYPE = MariaDBIntType(unsigned=True, zerofill=True)
SINGLE_SQL_TYPE_MARKER = UseSqlType(SINGLE_SQL_TYPE)


class SingleKeyDeclarations:
    __table_name__ = "ddl_source_single_key"
    __primary_key__ = "record_pk"

    record_id: Annotated[
        int,
        UseColumn("record_pk"),
        SINGLE_SQL_TYPE_MARKER,
    ]


class SyncSingleKey(SingleKeyDeclarations, ActiveRecord):
    pass


class AsyncSingleKey(SingleKeyDeclarations, AsyncActiveRecord):
    pass


def test_models_satisfy_ddl_source_and_preserve_field_order():
    for model in (SyncDDLSource, AsyncDDLSource):
        assert isinstance(model, DDLSource)
        assert model.ddl_field_names() == MODEL_FIELDS
        assert model.field_python_type("tenant_id") is int
        assert model.field_is_optional("optional_note") is True
        assert model.field_is_optional("status") is False


def test_field_markers_preserve_declared_objects_and_order():
    assert SyncDDLSource.column_type("tenant_id") is SQL_TYPE_MARKER
    assert SyncDDLSource.column_type("tenant_id").data_types == (
        SQL_TYPE,
        FALLBACK_SQL_TYPE,
    )
    assert SyncDDLSource.column_type("tenant_id").data_types[0] is SQL_TYPE

    constraints = SyncDDLSource.column_constraints("status")
    assert constraints[0] is DEFAULT_CONSTRAINT.constraint
    assert constraints[1] is UNIQUE_CONSTRAINT.constraint
    assert constraints[0].default_value is DEFAULT_VALUE
    assert [item.constraint_type for item in constraints] == [
        ColumnConstraintType.DEFAULT,
        ColumnConstraintType.UNIQUE,
        ColumnConstraintType.NOT_NULL,
    ]

    attributes = SyncDDLSource.column_attributes("status")
    assert attributes == [COLLATION, CHARACTER_SET, IDENTITY]
    assert attributes[0] is COLLATION
    assert attributes[1] is CHARACTER_SET
    assert attributes[2] is IDENTITY
    assert SyncDDLSource.column_comment("status") == COMMENT.comment
    assert SyncDDLSource.generated_column("computed") is GENERATED

    indexes = SyncDDLSource.column_indexes("label")
    assert [index.name for index in indexes] == [FIRST_INDEX.name, SECOND_INDEX.name]
    assert all(index.columns == ["display_label"] for index in indexes)
    assert indexes[0].unique is True
    assert indexes[0].include_columns is FIRST_INDEX.include_columns
    assert indexes[0].if_not_exists is True
    assert indexes[0].tablespace == FIRST_INDEX.tablespace

    assert SyncDDLSource.column_options("option_one") is COLUMN_OPTION
    options = SyncDDLSource.column_options("option_many")
    assert options == [COLUMN_OPTION, SECOND_COLUMN_OPTION]
    assert options[0] is COLUMN_OPTION
    assert options[1] is SECOND_COLUMN_OPTION


def test_backend_types_and_column_options_are_collected_without_dialect_selection():
    sql_type = SyncDDLSource.column_type("tenant_id")
    assert isinstance(sql_type, UseSqlType)
    assert isinstance(sql_type.data_type, MariaDBIntType)
    assert sql_type.data_type.unsigned is True
    assert sql_type.data_types[1] is FALLBACK_SQL_TYPE

    option = SyncDDLSource.column_options("option_one")
    assert isinstance(option, MariaDBColumnOptions)
    assert option.character_set == "utf8mb4"
    assert option.column_format is MariaDBColumnFormat.FIXED
    assert option.storage is MariaDBColumnStorage.MEMORY
    assert option.invisible is True


def test_primary_keys_use_physical_column_names_and_declaration_order():
    assert SyncDDLSource.columns_name() == {
        "tenant_id": "tenant_key",
        "order_id": "order_key",
        "status": "status",
        "label": "display_label",
        "computed": "computed",
        "option_one": "option_one",
        "option_many": "option_many",
        "optional_note": "optional_note",
    }

    for field in ("tenant_id", "order_id"):
        constraint_types = [
            item.constraint_type for item in SyncDDLSource.column_constraints(field)
        ]
        assert ColumnConstraintType.PRIMARY_KEY not in constraint_types
        assert ColumnConstraintType.NOT_NULL in constraint_types

    single_types = [
        item.constraint_type for item in SyncSingleKey.column_constraints("record_id")
    ]
    assert single_types == [
        ColumnConstraintType.PRIMARY_KEY,
        ColumnConstraintType.NOT_NULL,
    ]
    assert SyncSingleKey.columns_name() == {"record_id": "record_pk"}
    assert SyncSingleKey.column_type("record_id") is SINGLE_SQL_TYPE_MARKER
    assert SyncSingleKey.table_constraints() == []


def test_table_declarations_preserve_identity_order_and_composite_primary_key():
    constraints = SyncDDLSource.table_constraints()
    assert constraints is not TABLE_CONSTRAINTS
    assert constraints[0] is TABLE_CONSTRAINTS[0]
    assert constraints[1] is TABLE_CONSTRAINTS[1]
    assert [item.constraint_type for item in constraints] == [
        TableConstraintType.FOREIGN_KEY,
        TableConstraintType.UNIQUE,
        TableConstraintType.PRIMARY_KEY,
    ]
    assert constraints[2].columns == ["tenant_key", "order_key"]
    assert len(TABLE_CONSTRAINTS) == 2

    indexes = SyncDDLSource.table_indexes()
    assert indexes is not TABLE_INDEXES
    assert indexes[0] is TABLE_INDEXES[0]
    assert [index.name for index in indexes] == ["idx_table_status"]

    assert SyncDDLSource.table_options() is TABLE_OPTIONS
    assert SyncDDLSource.table_options()[0] is TABLE_OPTIONS[0]
    assert isinstance(TABLE_OPTIONS[0], MariaDBCreateTableOptions)
    assert TABLE_OPTIONS[0].engine == "InnoDB"
    assert SyncDDLSource.table_storage_options() is STORAGE_OPTIONS
    assert SyncDDLSource.table_storage_options()[0] is STORAGE_OPTIONS[0]
    assert SyncDDLSource.table_partition() is TABLE_PARTITION
    assert SyncDDLSource.table_inherits() is TABLE_INHERITS
    assert SyncDDLSource.table_tablespace() == TABLE_TABLESPACE


def test_collected_table_options_render_with_mariadb_dialect():
    table_options = SyncDDLSource.table_options()
    expression = CreateTableExpression(
        DIALECT,
        "ddl_source_orders",
        [ColumnDefinition(DIALECT, "id", IntegerType(DIALECT))],
        table_options=table_options[0],
    )
    sql, params = expression.to_sql()
    assert sql.startswith("CREATE TABLE `ddl_source_orders`")
    assert "ENGINE=" in sql and "InnoDB" in sql
    assert "DEFAULT CHARSET=" in sql and "utf8mb4" in sql
    assert "AUTO_INCREMENT=100" in sql
    assert params == ()


def test_batch_interfaces_cover_all_fields_and_preserve_selected_order():
    selected = ["label", "status", "tenant_id", "optional_note"]
    for model in (SyncDDLSource, AsyncDDLSource):
        for method_name in BATCH_METHODS:
            method = getattr(model, method_name)
            assert tuple(method()) == MODEL_FIELDS
            assert tuple(method(selected)) == tuple(selected)

        assert model.columns_name(selected) == {
            "label": "display_label",
            "status": "status",
            "tenant_id": "tenant_key",
            "optional_note": "optional_note",
        }
        assert model.columns_type(selected)["tenant_id"] is SQL_TYPE_MARKER
        assert model.columns_constraints(selected)["status"][0] is DEFAULT_CONSTRAINT.constraint
        assert model.columns_attributes(selected)["status"][0] is COLLATION
        assert model.columns_comment(selected)["status"] == COMMENT.comment
        assert model.columns_generated(selected)["optional_note"] is None
        assert model.columns_options(selected)["optional_note"] is None


def test_sync_and_async_sources_collect_the_same_declarations():
    assert AsyncDDLSource.column_type("tenant_id") is SyncDDLSource.column_type("tenant_id")
    assert AsyncDDLSource.column_comment("status") == SyncDDLSource.column_comment("status")
    assert AsyncDDLSource.generated_column("computed") is GENERATED
    assert AsyncDDLSource.column_options("option_one") is COLUMN_OPTION
    assert SyncDDLSource.column_options("option_many") == [
        COLUMN_OPTION,
        SECOND_COLUMN_OPTION,
    ]
    assert AsyncDDLSource.column_options("option_many") == [
        COLUMN_OPTION,
        SECOND_COLUMN_OPTION,
    ]

    sync_attributes = SyncDDLSource.column_attributes("status")
    async_attributes = AsyncDDLSource.column_attributes("status")
    assert all(left is right for left, right in zip(sync_attributes, async_attributes))

    sync_constraints = SyncDDLSource.column_constraints("status")
    async_constraints = AsyncDDLSource.column_constraints("status")
    assert sync_constraints[0] is async_constraints[0]
    assert sync_constraints[1] is async_constraints[1]
    assert [item.constraint_type for item in async_constraints] == [
        item.constraint_type for item in sync_constraints
    ]

    sync_indexes = SyncDDLSource.column_indexes("label")
    async_indexes = AsyncDDLSource.column_indexes("label")
    assert [index.name for index in async_indexes] == [index.name for index in sync_indexes]
    assert [index.columns for index in async_indexes] == [
        index.columns for index in sync_indexes
    ]

    assert AsyncDDLSource.table_options() is TABLE_OPTIONS
    assert AsyncDDLSource.table_storage_options() is STORAGE_OPTIONS
    assert AsyncDDLSource.table_partition() is TABLE_PARTITION
    assert AsyncDDLSource.table_inherits() is TABLE_INHERITS
    assert AsyncDDLSource.table_tablespace() == TABLE_TABLESPACE
    assert AsyncDDLSource.table_indexes()[0] is TABLE_INDEXES[0]

    sync_table_constraints = SyncDDLSource.table_constraints()
    async_table_constraints = AsyncDDLSource.table_constraints()
    assert sync_table_constraints[0] is async_table_constraints[0]
    assert sync_table_constraints[1] is async_table_constraints[1]
    assert async_table_constraints[2].columns == ["tenant_key", "order_key"]

    for model in (SyncSingleKey, AsyncSingleKey):
        assert [item.constraint_type for item in model.column_constraints("record_id")] == [
            ColumnConstraintType.PRIMARY_KEY,
            ColumnConstraintType.NOT_NULL,
        ]
        assert model.column_name("record_id") == "record_pk"
        assert model.column_type("record_id") is SINGLE_SQL_TYPE_MARKER
