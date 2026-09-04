# ddl tests

MariaDB DDL coverage: ALTER TABLE IF [NOT] EXISTS qualifiers, auto-increment / defaults regressions, expression-level CreateTableExpression.diff() for the MariaDB dialect (in-place MODIFY COLUMN), CREATE TABLE ... LIKE, storage options / comments / ENUM / SET features and DDL gap features (RENAME, TRUNCATE, index renaming, maintenance, routines, admin statements).

## Key files

- `test_alter_table_if_exists_modifiers.py` — IF [NOT] EXISTS qualifiers
- `test_auto_increment_ddl.py` — auto-increment regressions
- `test_create_table_expression_diff.py` — CreateTableExpression.diff() with MariaDB overrides
- `test_create_table_like.py` — CREATE TABLE ... LIKE
- `test_ddl_features.py` — ENGINE/CHARSET/COMMENT/ENUM/SET features
- `test_ddl_gap_features.py` — RENAME/TRUNCATE/maintenance/routines/admin coverage
