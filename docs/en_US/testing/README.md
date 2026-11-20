<!-- docs/en_US/testing/README.md -->
# Testing

This backend is exercised against real MariaDB servers through the standardized
ActiveRecord testsuite. The generic test strategy and fixtures belong to the
[core testing manual](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US/testing);
this chapter covers what is specific to running them here.

## Chapters

- [Test configuration](configuration.md)
- [Local testing](local.md)

## Scope rules

- Tests are split by feature category (DDL, DML, query, transaction,
  introspection, and so on) so a change can be verified against a narrow slice.
- Version-gated features are marked with a `requires_capability` or
  `requires_protocol` marker; a server below the feature's floor skips the
  case rather than failing it.
- The CI matrix covers the supported MariaDB versions and is the only place a
  full-suite run happens. Local runs should target the change at hand.

## Quick check

```bash
# from the repository root, with the venv activated
PYTHONPATH=tests .venv3.14/Scripts/python.exe -m pytest tests/test_transaction.py -q
```

See [Local testing](local.md) for the environment layout and provider setup.
