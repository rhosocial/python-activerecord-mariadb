# tests/providers/basic.py
"""
This file provides the concrete implementation of the `IBasicProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.
"""
import os
import sys
import logging
from typing import Type, List, Tuple, Optional

logger = logging.getLogger(__name__)

from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.model import ActiveRecord

from rhosocial.activerecord.testsuite.utils import select_fixture

from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    User as UserBase, TypeCase as TypeCaseBase, ValidatedFieldUser as ValidatedFieldUserBase,
    TypeTestModel as TypeTestModelBase, ValidatedUser as ValidatedUserBase,
    TypeAdapterTest as TypeAdapterTestBase, YesOrNoBooleanAdapter,
    MappedUser as MappedUserBase, MappedPost as MappedPostBase, MappedComment as MappedCommentBase,
    ColumnMappingModel as ColumnMappingModelBase, MixedAnnotationModel as MixedAnnotationModelBase
)
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    AsyncUser as AsyncUserBase, AsyncTypeCase as AsyncTypeCaseBase,
    AsyncValidatedUser as AsyncValidatedUserBase, AsyncValidatedFieldUser as AsyncValidatedFieldUserBase,
    AsyncTypeTestModel as AsyncTypeTestModelBase, AsyncTypeAdapterTest as AsyncTypeAdapterTestBase,
    AsyncMappedUser as AsyncMappedUserBase, AsyncMappedPost as AsyncMappedPostBase,
    AsyncMappedComment as AsyncMappedCommentBase,
    AsyncColumnMappingModel as AsyncColumnMappingModelBase, AsyncMixedAnnotationModel as AsyncMixedAnnotationModelBase
)

User310 = TypeCase310 = ValidatedFieldUser310 = TypeTestModel310 = ValidatedUser310 = None
TypeAdapterTest310 = MappedUser310 = MappedPost310 = MappedComment310 = None
ColumnMappingModel310 = MixedAnnotationModel310 = None
AsyncUser310 = AsyncTypeCase310 = AsyncValidatedFieldUser310 = AsyncTypeTestModel310 = None
AsyncValidatedUser310 = AsyncTypeAdapterTest310 = AsyncMappedUser310 = AsyncMappedPost310 = None
AsyncMappedComment310 = AsyncColumnMappingModel310 = AsyncMixedAnnotationModel310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py310 import (
            User as User310, TypeCase as TypeCase310, ValidatedFieldUser as ValidatedFieldUser310,
            TypeTestModel as TypeTestModel310, ValidatedUser as ValidatedUser310,
            TypeAdapterTest as TypeAdapterTest310,
            MappedUser as MappedUser310, MappedPost as MappedPost310, MappedComment as MappedComment310,
            ColumnMappingModel as ColumnMappingModel310, MixedAnnotationModel as MixedAnnotationModel310
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py310 import (
            AsyncUser as AsyncUser310, AsyncTypeCase as AsyncTypeCase310,
            AsyncValidatedUser as AsyncValidatedUser310, AsyncValidatedFieldUser as AsyncValidatedFieldUser310,
            AsyncTypeTestModel as AsyncTypeTestModel310, AsyncTypeAdapterTest as AsyncTypeAdapterTest310,
            AsyncMappedUser as AsyncMappedUser310, AsyncMappedPost as AsyncMappedPost310,
            AsyncMappedComment as AsyncMappedComment310,
            AsyncColumnMappingModel as AsyncColumnMappingModel310, AsyncMixedAnnotationModel as AsyncMixedAnnotationModel310
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

User311 = TypeCase311 = ValidatedFieldUser311 = TypeTestModel311 = ValidatedUser311 = None
TypeAdapterTest311 = MappedUser311 = MappedPost311 = MappedComment311 = None
ColumnMappingModel311 = MixedAnnotationModel311 = None
AsyncUser311 = AsyncTypeCase311 = AsyncValidatedFieldUser311 = AsyncTypeTestModel311 = None
AsyncValidatedUser311 = AsyncTypeAdapterTest311 = AsyncMappedUser311 = AsyncMappedPost311 = None
AsyncMappedComment311 = AsyncColumnMappingModel311 = AsyncMixedAnnotationModel311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py311 import (
            User as User311, TypeCase as TypeCase311, ValidatedFieldUser as ValidatedFieldUser311,
            TypeTestModel as TypeTestModel311, ValidatedUser as ValidatedUser311,
            TypeAdapterTest as TypeAdapterTest311,
            MappedUser as MappedUser311, MappedPost as MappedPost311, MappedComment as MappedComment311,
            ColumnMappingModel as ColumnMappingModel311, MixedAnnotationModel as MixedAnnotationModel311
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py311 import (
            AsyncUser as AsyncUser311, AsyncTypeCase as AsyncTypeCase311,
            AsyncValidatedUser as AsyncValidatedUser311, AsyncValidatedFieldUser as AsyncValidatedFieldUser311,
            AsyncTypeTestModel as AsyncTypeTestModel311, AsyncTypeAdapterTest as AsyncTypeAdapterTest311,
            AsyncMappedUser as AsyncMappedUser311, AsyncMappedPost as AsyncMappedPost311,
            AsyncMappedComment as AsyncMappedComment311,
            AsyncColumnMappingModel as AsyncColumnMappingModel311, AsyncMixedAnnotationModel as AsyncMixedAnnotationModel311
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

User312 = TypeCase312 = ValidatedFieldUser312 = TypeTestModel312 = ValidatedUser312 = None
TypeAdapterTest312 = MappedUser312 = MappedPost312 = MappedComment312 = None
ColumnMappingModel312 = MixedAnnotationModel312 = None
AsyncUser312 = AsyncTypeCase312 = AsyncValidatedFieldUser312 = AsyncTypeTestModel312 = None
AsyncValidatedUser312 = AsyncTypeAdapterTest312 = AsyncMappedUser312 = AsyncMappedPost312 = None
AsyncMappedComment312 = AsyncColumnMappingModel312 = AsyncMixedAnnotationModel312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py312 import (
            User as User312, TypeCase as TypeCase312, ValidatedFieldUser as ValidatedFieldUser312,
            TypeTestModel as TypeTestModel312, ValidatedUser as ValidatedUser312,
            TypeAdapterTest as TypeAdapterTest312,
            MappedUser as MappedUser312, MappedPost as MappedPost312, MappedComment as MappedComment312,
            ColumnMappingModel as ColumnMappingModel312, MixedAnnotationModel as MixedAnnotationModel312
        )
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models_py312 import (
            AsyncUser as AsyncUser312, AsyncTypeCase as AsyncTypeCase312,
            AsyncValidatedUser as AsyncValidatedUser312, AsyncValidatedFieldUser as AsyncValidatedFieldUser312,
            AsyncTypeTestModel as AsyncTypeTestModel312, AsyncTypeAdapterTest as AsyncTypeAdapterTest312,
            AsyncMappedUser as AsyncMappedUser312, AsyncMappedPost as AsyncMappedPost312,
            AsyncMappedComment as AsyncMappedComment312,
            AsyncColumnMappingModel as AsyncColumnMappingModel312, AsyncMixedAnnotationModel as AsyncMixedAnnotationModel312
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.12+ fixtures: {e}")


def _select_model_class(base_cls, py312_cls, py311_cls, py310_cls, model_name: str) -> Type:
    """Select the most appropriate model class for the current Python version."""
    candidates = [c for c in [py312_cls, py311_cls, py310_cls, base_cls] if c is not None]
    selected = select_fixture(*candidates)
    logger.info(f"Selected {model_name}: {selected.__name__} from {selected.__module__}")
    return selected


User = _select_model_class(UserBase, User312, User311, User310, "User")
TypeCase = _select_model_class(TypeCaseBase, TypeCase312, TypeCase311, TypeCase310, "TypeCase")
ValidatedFieldUser = _select_model_class(ValidatedFieldUserBase, ValidatedFieldUser312, ValidatedFieldUser311, ValidatedFieldUser310, "ValidatedFieldUser")
TypeTestModel = _select_model_class(TypeTestModelBase, TypeTestModel312, TypeTestModel311, TypeTestModel310, "TypeTestModel")
ValidatedUser = _select_model_class(ValidatedUserBase, ValidatedUser312, ValidatedUser311, ValidatedUser310, "ValidatedUser")
TypeAdapterTest = _select_model_class(TypeAdapterTestBase, TypeAdapterTest312, TypeAdapterTest311, TypeAdapterTest310, "TypeAdapterTest")
MappedUser = _select_model_class(MappedUserBase, MappedUser312, MappedUser311, MappedUser310, "MappedUser")
MappedPost = _select_model_class(MappedPostBase, MappedPost312, MappedPost311, MappedPost310, "MappedPost")
MappedComment = _select_model_class(MappedCommentBase, MappedComment312, MappedComment311, MappedComment310, "MappedComment")
ColumnMappingModel = _select_model_class(ColumnMappingModelBase, ColumnMappingModel312, ColumnMappingModel311, ColumnMappingModel310, "ColumnMappingModel")
MixedAnnotationModel = _select_model_class(MixedAnnotationModelBase, MixedAnnotationModel312, MixedAnnotationModel311, MixedAnnotationModel310, "MixedAnnotationModel")

AsyncUser = _select_model_class(AsyncUserBase, AsyncUser312, AsyncUser311, AsyncUser310, "AsyncUser")
AsyncTypeCase = _select_model_class(AsyncTypeCaseBase, AsyncTypeCase312, AsyncTypeCase311, AsyncTypeCase310, "AsyncTypeCase")
AsyncValidatedFieldUser = _select_model_class(AsyncValidatedFieldUserBase, AsyncValidatedFieldUser312, AsyncValidatedFieldUser311, AsyncValidatedFieldUser310, "AsyncValidatedFieldUser")
AsyncTypeTestModel = _select_model_class(AsyncTypeTestModelBase, AsyncTypeTestModel312, AsyncTypeTestModel311, AsyncTypeTestModel310, "AsyncTypeTestModel")
AsyncValidatedUser = _select_model_class(AsyncValidatedUserBase, AsyncValidatedUser312, AsyncValidatedUser311, AsyncValidatedUser310, "AsyncValidatedUser")
AsyncTypeAdapterTest = _select_model_class(AsyncTypeAdapterTestBase, AsyncTypeAdapterTest312, AsyncTypeAdapterTest311, AsyncTypeAdapterTest310, "AsyncTypeAdapterTest")
AsyncMappedUser = _select_model_class(AsyncMappedUserBase, AsyncMappedUser312, AsyncMappedUser311, AsyncMappedUser310, "AsyncMappedUser")
AsyncMappedPost = _select_model_class(AsyncMappedPostBase, AsyncMappedPost312, AsyncMappedPost311, AsyncMappedPost310, "AsyncMappedPost")
AsyncMappedComment = _select_model_class(AsyncMappedCommentBase, AsyncMappedComment312, AsyncMappedComment311, AsyncMappedComment310, "AsyncMappedComment")
AsyncColumnMappingModel = _select_model_class(AsyncColumnMappingModelBase, AsyncColumnMappingModel312, AsyncColumnMappingModel311, AsyncColumnMappingModel310, "AsyncColumnMappingModel")
AsyncMixedAnnotationModel = _select_model_class(AsyncMixedAnnotationModelBase, AsyncMixedAnnotationModel312, AsyncMixedAnnotationModel311, AsyncMixedAnnotationModel310, "AsyncMixedAnnotationModel")

from rhosocial.activerecord.testsuite.feature.basic.interfaces import IBasicProvider
from .scenarios import get_enabled_scenarios, get_scenario


class BasicProvider(IBasicProvider):
    """MariaDB backend implementation for the basic features test group."""

    def __init__(self):
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _track_backend(self, backend_instance, collection: List) -> None:
        if backend_instance not in collection:
            collection.append(backend_instance)

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        backend_class, config = get_scenario(scenario_name)
        model_class.configure(config, backend_class)

        backend_instance = model_class.__backend__
        self._track_backend(backend_instance, self._active_backends)

        self._reset_table_sync(model_class, table_name)
        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given async model."""
        from rhosocial.activerecord.backend.impl.mariadb import AsyncMariaDBBackend

        _, config = get_scenario(scenario_name)
        await model_class.configure(config, AsyncMariaDBBackend)

        backend_instance = model_class.__backend__
        self._track_backend(backend_instance, self._active_async_backends)

        await self._reset_table_async(model_class, table_name)
        return model_class

    def _reset_table_sync(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        try:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        finally:
            model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema_sql = self._load_mariadb_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)

    async def _reset_table_async(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        try:
            await model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 0")
            await model_class.__backend__.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        finally:
            await model_class.__backend__.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema_sql = self._load_mariadb_schema(f"{table_name}.sql")
        await model_class.__backend__.execute(schema_sql)

    async def _initialize_async_model_schema(self, model_class: Type[ActiveRecord], table_name: str):
        """Initialize schema for a model that shares backend with another model."""
        await self._reset_table_async(model_class, table_name)

    def _initialize_model_schema(self, model_class: Type[ActiveRecord], table_name: str) -> None:
        """Initialize schema for a model that shares backend with another model."""
        self._reset_table_sync(model_class, table_name)

    def _setup_multiple_models(self, model_classes: List[Tuple[Type[ActiveRecord], str]], scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Helper to set up multiple related models for a test, sharing a single backend."""
        if not model_classes:
            return tuple()

        first_model_class, first_table_name = model_classes[0]
        first_model = self._setup_model(first_model_class, scenario_name, first_table_name)
        shared_backend = first_model.__backend__

        result = [first_model]

        for model_class, table_name in model_classes[1:]:
            model_class.__connection_config__ = first_model.__connection_config__
            model_class.__backend_class__ = first_model.__backend_class__
            model_class.__backend__ = shared_backend
            self._track_backend(shared_backend, self._active_backends)
            self._initialize_model_schema(model_class, table_name)
            result.append(model_class)

        return tuple(result)

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for user model tests."""
        return self._setup_model(User, scenario_name, "users")

    async def setup_async_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async user model tests."""
        return await self._setup_async_model(AsyncUser, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type case model tests."""
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    async def setup_async_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type case model tests."""
        return await self._setup_async_model(AsyncTypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for type test model tests."""
        import pytest
        backend_class, config = get_scenario(scenario_name)
        temp_backend = backend_class(connection_config=config)
        temp_backend.connect()
        actual_version = temp_backend.get_server_version()
        temp_backend.disconnect()
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        temp_dialect = MariaDBDialect(actual_version)
        if not temp_dialect.supports_json_type():
            pytest.skip(f"JSON functions not supported by MariaDB version {actual_version}")
        model = self._setup_model(TypeTestModel, scenario_name, "type_tests")
        return model

    async def setup_async_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async type test model tests."""
        import pytest
        from rhosocial.activerecord.backend.impl.mariadb import AsyncMariaDBBackend
        _, config = get_scenario(scenario_name)
        temp_backend = AsyncMariaDBBackend(connection_config=config)
        await temp_backend.connect()
        actual_version = await temp_backend.get_server_version()
        await temp_backend.disconnect()
        from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
        temp_dialect = MariaDBDialect(actual_version)
        if not temp_dialect.supports_json_type():
            pytest.skip(f"JSON functions not supported by MariaDB version {actual_version}")
        model = await self._setup_async_model(AsyncTypeTestModel, scenario_name, "type_tests")
        return model

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated field user model tests."""
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_async_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated field user model tests."""
        return await self._setup_async_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for validated user model tests."""
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    async def setup_async_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for async validated user model tests."""
        return await self._setup_async_model(AsyncValidatedUser, scenario_name, "validated_users")

    def setup_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        return self._setup_multiple_models([
            (MappedUser, "users"),
            (MappedPost, "posts"),
            (MappedComment, "comments")
        ], scenario_name)

    async def setup_async_mapped_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for AsyncMappedUser, AsyncMappedPost, and AsyncMappedComment models."""
        user = await self._setup_async_model(AsyncMappedUser, scenario_name, "users")
        shared_backend = user.__backend__

        post_model_class = AsyncMappedPost
        post_model_class.__connection_config__ = user.__connection_config__
        post_model_class.__backend_class__ = user.__backend_class__
        post_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(post_model_class, "posts")

        comment_model_class = AsyncMappedComment
        comment_model_class.__connection_config__ = user.__connection_config__
        comment_model_class.__backend_class__ = user.__backend_class__
        comment_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(comment_model_class, "comments")

        return user, post_model_class, comment_model_class

    def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for ColumnMappingModel and MixedAnnotationModel."""
        return self._setup_multiple_models([
            (ColumnMappingModel, "column_mapping_items"),
            (MixedAnnotationModel, "mixed_annotation_items")
        ], scenario_name)

    async def setup_async_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for AsyncColumnMappingModel and AsyncMixedAnnotationModel."""
        column_mapping_model = await self._setup_async_model(AsyncColumnMappingModel, scenario_name, "column_mapping_items")
        shared_backend = column_mapping_model.__backend__

        mixed_annotation_model_class = AsyncMixedAnnotationModel
        mixed_annotation_model_class.__connection_config__ = column_mapping_model.__connection_config__
        mixed_annotation_model_class.__backend_class__ = column_mapping_model.__backend_class__
        mixed_annotation_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(mixed_annotation_model_class, "mixed_annotation_items")

        return column_mapping_model, mixed_annotation_model_class

    def setup_type_adapter_model_and_schema(self, scenario_name: Optional[str] = None) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeAdapterTest` model tests."""
        if scenario_name is None:
            scenario_name = self.get_test_scenarios()[0] if self.get_test_scenarios() else "default"
        return self._setup_model(TypeAdapterTest, scenario_name, "type_adapter_tests")

    async def setup_async_type_adapter_model_and_schema(self, scenario_name: Optional[str] = None) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeAdapterTest` model tests."""
        if scenario_name is None:
            scenario_name = self.get_test_scenarios()[0] if self.get_test_scenarios() else "default"
        return await self._setup_async_model(AsyncTypeAdapterTest, scenario_name, "type_adapter_tests")

    def get_yes_no_adapter(self) -> 'BaseSQLTypeAdapter':
        """Returns an instance of the YesOrNoBooleanAdapter."""
        return YesOrNoBooleanAdapter()

    def _load_mariadb_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_mariadb_test", "feature", "basic", "schema")
        schema_path = os.path.join(schema_dir, filename)

        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """Performs cleanup after a test, dropping all tables and disconnecting backends."""
        tables_to_drop = [
            'users', 'type_cases', 'type_tests', 'validated_field_users',
            'validated_users', 'type_adapter_tests', 'posts', 'comments',
            'column_mapping_items', 'mixed_annotation_items'
        ]
        for backend_instance in self._active_backends:
            try:
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table_name in tables_to_drop:
                    try:
                        backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                    except Exception:
                        pass
                backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
            finally:
                try:
                    backend_instance.disconnect()
                except Exception:
                    pass

        self._active_backends.clear()

    async def cleanup_after_test_async(self, scenario_name: str):
        """Performs async cleanup after a test, dropping all tables and disconnecting backends."""
        tables_to_drop = [
            'users', 'type_cases', 'type_tests', 'validated_field_users',
            'validated_users', 'type_adapter_tests', 'posts', 'comments',
            'column_mapping_items', 'mixed_annotation_items'
        ]
        for backend_instance in self._active_async_backends:
            try:
                try:
                    await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 0")
                    for table_name in tables_to_drop:
                        try:
                            await backend_instance.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                        except Exception:
                            pass
                    await backend_instance.execute("SET FOREIGN_KEY_CHECKS = 1")
                except Exception:
                    pass
            finally:
                try:
                    await backend_instance.disconnect()
                except Exception:
                    pass

        self._active_async_backends.clear()
