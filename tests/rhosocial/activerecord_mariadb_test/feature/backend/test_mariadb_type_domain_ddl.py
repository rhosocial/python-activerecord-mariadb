# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_mariadb_type_domain_ddl.py
"""Negative TYPE and DOMAIN DDL contracts for MariaDB."""

import pytest

from rhosocial.activerecord.backend.dialect import (
    DomainMixin,
    DomainSupport,
    UserDefinedTypeMixin,
    UserDefinedTypeSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Literal
from rhosocial.activerecord.backend.expression.statements import (
    AlterDomainExpression,
    AlterTypeExpression,
    CreateDomainExpression,
    CreateTypeExpression,
    DomainCheckConstraint,
    DomainNullability,
    DomainValueExpression,
    DropDomainDefaultAction,
    DropDomainExpression,
    DropTypeExpression,
    TypeAlterAction,
    TypeDefinition,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.backend.impl.mariadb.expression.types import (
    MariaDBEnumType,
    MariaDBSetType,
)


class _NegativeTypeDefinition(TypeDefinition):
    @property
    def definition_kind(self) -> str:
        return "negative"


class _NegativeTypeAlterAction(TypeAlterAction):
    @property
    def action_kind(self) -> str:
        return "negative"


@pytest.fixture
def dialect():
    return MariaDBDialect(version=(10, 6, 0))


TYPE_DOMAIN_SUPPORT_METHODS = (
    "supports_type_objects",
    "supports_create_type",
    "supports_alter_type",
    "supports_drop_type",
    "supports_create_type_if_not_exists",
    "supports_create_type_or_replace",
    "supports_alter_type_if_exists",
    "supports_drop_type_if_exists",
    "supports_multiple_type_alter_actions",
    "supports_domains",
    "supports_create_domain",
    "supports_alter_domain",
    "supports_drop_domain",
    "supports_domain_default",
    "supports_domain_checks",
    "supports_named_domain_checks",
    "supports_multiple_domain_checks",
    "supports_domain_collation",
    "supports_multiple_domain_alter_actions",
    "supports_drop_domain_if_exists",
    "supports_drop_domain_cascade",
    "supports_drop_domain_restrict",
    "supports_unnamed_domain_check_drop",
)

TYPE_FORMATTERS = (
    "format_create_type_statement",
    "format_alter_type_statement",
    "format_drop_type_statement",
    "format_type_definition",
    "format_type_alter_action",
)

DOMAIN_FORMATTERS = (
    "format_create_domain_statement",
    "format_alter_domain_statement",
    "format_drop_domain_statement",
    "format_domain_value_expression",
    "format_domain_check_constraint",
    "format_domain_alter_action",
)


@pytest.mark.parametrize("method_name", TYPE_DOMAIN_SUPPORT_METHODS)
def test_schema_level_type_domain_support_is_false(dialect, method_name):
    assert getattr(dialect, method_name)() is False


@pytest.mark.parametrize("nullability", tuple(DomainNullability))
def test_domain_nullability_support_is_false(dialect, nullability):
    assert dialect.supports_domain_nullability(nullability) is False


def test_type_and_domain_definition_support_is_empty(dialect):
    assert dialect.supported_type_definitions() == ()
    assert dialect.supports_type_definition(_NegativeTypeDefinition) is False
    assert dialect.supports_type_alter_action(_NegativeTypeAlterAction) is False
    assert dialect.supports_alter_domain_action(DropDomainDefaultAction) is False


def test_type_and_domain_protocols_are_composed(dialect):
    assert isinstance(dialect, UserDefinedTypeSupport)
    assert isinstance(dialect, DomainSupport)
    assert isinstance(dialect, UserDefinedTypeMixin)
    assert isinstance(dialect, DomainMixin)

    for mixin, protocol in (
        (UserDefinedTypeMixin, UserDefinedTypeSupport),
        (DomainMixin, DomainSupport),
    ):
        assert mixin in MariaDBDialect.__mro__
        assert protocol in MariaDBDialect.__mro__
        assert MariaDBDialect.__mro__.index(mixin) < MariaDBDialect.__mro__.index(protocol)


def test_core_type_and_domain_formatters_own_the_mro():
    for method_name in TYPE_FORMATTERS:
        assert getattr(MariaDBDialect, method_name) is getattr(
            UserDefinedTypeMixin,
            method_name,
        )
    for method_name in DOMAIN_FORMATTERS:
        assert getattr(MariaDBDialect, method_name) is getattr(
            DomainMixin,
            method_name,
        )


def test_type_and_domain_formatters_and_expressions_fail_fast(dialect):
    definition = _NegativeTypeDefinition(dialect)
    alter_action = _NegativeTypeAlterAction(dialect)
    domain_action = DropDomainDefaultAction(dialect)
    condition = DomainValueExpression(dialect) > Literal(
        dialect,
        0,
        inline_literals=True,
    )
    check = DomainCheckConstraint(dialect, condition)
    expressions = (
        ("format_create_type_statement", CreateTypeExpression(dialect, "status", definition)),
        (
            "format_alter_type_statement",
            AlterTypeExpression(dialect, "status", [alter_action]),
        ),
        ("format_drop_type_statement", DropTypeExpression(dialect, "status")),
        ("format_type_definition", definition),
        ("format_type_alter_action", alter_action),
        (
            "format_create_domain_statement",
            CreateDomainExpression(dialect, "positive", IntegerType(dialect)),
        ),
        (
            "format_alter_domain_statement",
            AlterDomainExpression(dialect, "positive", [domain_action]),
        ),
        ("format_drop_domain_statement", DropDomainExpression(dialect, "positive")),
        ("format_domain_value_expression", DomainValueExpression(dialect)),
        ("format_domain_check_constraint", check),
        ("format_domain_alter_action", domain_action),
    )

    for method_name, expression in expressions:
        with pytest.raises(UnsupportedFeatureError):
            getattr(dialect, method_name)(expression)
        with pytest.raises(UnsupportedFeatureError):
            expression.to_sql()


def test_enum_and_set_remain_column_data_types(dialect):
    enum_sql, enum_params = MariaDBEnumType(dialect, ["pending", "done"]).to_sql()
    set_sql, set_params = MariaDBSetType(dialect, ["read", "write"]).to_sql()

    assert enum_sql == "ENUM('pending','done')"
    assert enum_params == ()
    assert set_sql == "SET('read','write')"
    assert set_params == ()


def test_sequence_support_remains_independent(dialect):
    assert dialect.supports_sequence() is True
    assert dialect.format_create_sequence_statement("job_ids") == (
        "CREATE SEQUENCE `job_ids`",
        (),
    )
