# cli tests

Tests for the MariaDB backend CLI subpackage: argument parsing, help output, serialization, provider factory, protocol-info building, named-expression / introspection / query / procedure arguments and display functions.

## Key files

- `test_cli.py` — CLI parse/help/serialize/provider/display coverage
- `test_cli_blackbox.py` — black-box CLI against the live scenario server (info/query/introspect/status/named-*)
