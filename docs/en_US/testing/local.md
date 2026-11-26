<!-- docs/en_US/testing/local.md -->
# Local testing

## Start a server

Any supported MariaDB release works; 12.3 (LTS) is the recommended baseline.
Create a database and a user with rights to create and drop tables:

```sql
CREATE DATABASE test_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app'@'%' IDENTIFIED BY 'secret';
GRANT ALL PRIVILEGES ON test_db.* TO 'app'@'%';
```

## Run a targeted check

Local testing must stay within the task at hand — do not run the whole suite.
Point the environment at your server and select one file or one test:

```powershell
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''
$env:MYSQL_HOST='127.0.0.1'; $env:MYSQL_DATABASE='test_db'
$env:MYSQL_USER='app'; $env:MYSQL_PASSWORD='secret'
$env:PYTHONPATH='tests'
.\.venv3.14\Scripts\python.exe -m pytest tests/test_introspection.py -q
```

A single case:

```powershell
.\.venv3.14\Scripts\python.exe -m pytest tests/test_introspection.py::test_get_partition_state -q
```

## Import/syntax smoke test

Documentation examples do not need a live server to be syntax-checked:

```powershell
.\.venv3.14\Scripts\python.exe -m py_compile docs/examples/chapter_04_ddl/ddl.py
```

## Static checks

```powershell
.\.venv3.14\Scripts\ruff.exe check src
.\.venv3.14\Scripts\black.exe --check src
.\.venv3.14\Scripts\isort.exe --check-only src
.\.venv3.14\Scripts\mypy.exe src
```

Line width is 100 for Black/isort and 120 for ruff (see `pyproject.toml`).

## Troubleshooting a local run

- `Access denied` — check the user/host pair and that the test database exists.
- `Unknown database` — the provider's database name must match the environment.
- Feature-gated skips — expected on a server below the feature floor; see
  [Version gates](../mariadb_specific_features/version_gates.md).
- Full-suite failures that you cannot reproduce locally belong to the CI
  matrix; keep local runs narrow.
