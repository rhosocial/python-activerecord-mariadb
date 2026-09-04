# tests/rhosocial/activerecord_mariadb_test/feature/backend/ddl/test_default_model_ddl.py
"""Default-type model rendering — MariaDB.

``DefaultUser`` declares plain Python types with no ``UseSqlType``; MariaDB
derives the column types via its own suggestion mapping.
"""

from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
from rhosocial.activerecord.examples.ddl_default_types import DefaultUser


def _render() -> str:
    sql, _ = DefaultUser.generate_create_table(dialect=MariaDBDialect()).to_sql()
    return sql


def test_default_user_has_no_explicit_sql_types():
    assert DefaultUser.__table_field_sql_types__ == {}


def test_mariadb_default_user_ddl_columns():
    sql = _render()
    assert "CREATE TABLE `default_users`" in sql
    assert "`id` INT PRIMARY KEY AUTO_INCREMENT" in sql
    assert "`username` TEXT NOT NULL" in sql
    assert "`email` TEXT NOT NULL" in sql
    assert "`is_active` TINYINT NOT NULL" in sql
    assert "`balance` DOUBLE NOT NULL" in sql
    assert "`created_at` DATETIME NOT NULL" in sql
    assert "`metadata` TEXT NOT NULL" in sql
    assert "`avatar` BLOB NOT NULL" in sql
    assert "`birthday` DATE" in sql