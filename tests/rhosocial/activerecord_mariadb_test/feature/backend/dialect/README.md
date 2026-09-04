# dialect tests

MariaDB dialect behavior: formatting against a real server, SQLFunctionSupport protocol and version-dependent availability and SQL-injection security fixes (escaping, JSON_TABLE validation).

## Key files

- `test_dialect_formatting.py` — dialect formatting integration
- `test_dialect_function_support.py` — supports_functions() and version gates
- `test_dialect_security.py` — escaping and validation security fixes
