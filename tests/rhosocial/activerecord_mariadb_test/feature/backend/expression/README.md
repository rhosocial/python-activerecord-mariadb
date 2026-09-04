# expression tests

MariaDB expression classes: serialization round trips, transaction expressions (SET TRANSACTION before START TRANSACTION), JSON expressions and the MariaDB SHOW expression classes (keyword-only parameters folded from the fluent API).

## Key files

- `test_expression_roundtrip_all.py` — serialization round trip for all MariaDB expressions
- `test_expressions_transaction.py` — transaction expression classes
- `test_json_expressions.py` — JSON extract/object/array/contains expressions
- `test_show_expressions.py` — SHOW expression classes (offline)
