<!-- docs/en_US/testing/configuration.md -->
# Test configuration

## Dependencies

Install the `test` extra plus the testsuite from local source:

```bash
.venv3.14/Scripts/pip install -e ".[test]" -i https://mirrors.aliyun.com/pypi/simple/
.venv3.14/Scripts/pip install -e ../python-activerecord-testsuite -i https://mirrors.aliyun.com/pypi/simple/
```

> The bare `rhosocial-activerecord-testsuite` name in the extra may resolve to an
> older published release; install the local checkout explicitly so the
> provider modules match the code under test.

## Provider registration

Tests find the provider through `providers/registry.py` on `PYTHONPATH`:

```bash
$env:PYTHONPATH = "tests"
.venv3.14/Scripts/python.exe -m pytest tests/test_feature.py -q
```

The provider builds a `MariaDBConnectionConfig` for the target server. Give each
test worker its own database or table prefix so parallel runs do not collide.

## Environment variables

The example scripts and the provider read connection settings from the
environment (the scripts default to the `MYSQL_` names used by the existing
harness):

| Variable | Meaning |
|----------|---------|
| `MYSQL_HOST` / `MARIADB_HOST` | Server host |
| `MYSQL_PORT` / `MARIADB_PORT` | Server port |
| `MYSQL_DATABASE` / `MARIADB_DATABASE` | Test database |
| `MYSQL_USER` / `MARIADB_USERNAME` | User |
| `MYSQL_PASSWORD` / `MARIADB_PASSWORD` | Password |

## Version gating in tests

A test that exercises a feature at or above a version floor carries a marker.
The dialect's `supports_*` probes are the source of truth — when adding a test
for a new version-dependent feature, add the floor to
`MARIADB_VERSION_BOUNDARIES` and gate the case on the corresponding probe.

## CI matrix

CI runs the suite across the supported releases (10.2 → 13.1-rc). A green local
run on 12.3 does not replace the matrix: version-specific rendering and
removals are only visible there.
