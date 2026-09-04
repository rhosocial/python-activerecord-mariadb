# introspection tests

The MariaDB introspection stack: tables, columns, indexes, foreign keys, triggers, views and database info, cache management, the lazily-created status property and SHOW command parsing.

## Key files

- `test_introspection_cache.py` — cache invalidation, expiration, thread safety
- `test_introspection_columns.py` — column metadata
- `test_introspection_database.py` — database info and capabilities
- `test_introspection_foreign_keys.py` — foreign keys
- `test_introspection_indexes.py` — indexes incl. primary key
- `test_introspection_status.py` — introspector status property
- `test_introspection_tables.py` — tables
- `test_introspection_triggers.py` — triggers
- `test_introspection_views.py` — views
- `test_show_functionality.py` — SHOW ... parsing
