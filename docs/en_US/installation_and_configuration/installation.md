<!-- docs/en_US/installation_and_configuration/installation.md -->
# Installation

## Requirements

- Python 3.8 or newer.
- A reachable MariaDB server with an existing database (10.2+; see
  [Supported versions](../introduction/supported_versions.md)).
- The `mariadb` connector (installed automatically as a dependency).

## Install from PyPI

```bash
pip install rhosocial-activerecord-mariadb
```

This pulls in `rhosocial-activerecord` and `mariadb`:

```
rhosocial-activerecord>=1.0.0.dev30,<2.0.0
mariadb>=2.0.0rc2
```

## Optional extras

```bash
pip install "rhosocial-activerecord-mariadb[pooling]"  # DBUtils>=3.0.0
pip install "rhosocial-activerecord-mariadb[test]"     # testsuite and pytest tooling
pip install "rhosocial-activerecord-mariadb[dev]"      # linters, formatters, type checker
pip install "rhosocial-activerecord-mariadb[docs]"     # Sphinx + MyST
```

> Note: when running against a local checkout, install the testsuite from the
> local source path rather than relying on the bare name in the `test` extra,
> which may resolve to an older published release.

## Install from source

```bash
git clone https://github.com/rhosocial/python-activerecord-mariadb.git
cd python-activerecord-mariadb
py -3.14 -m venv .venv3.14
.venv3.14/Scripts/pip install -e . -i https://mirrors.aliyun.com/pypi/simple/
```

The core library is a namespace package; both `rhosocial.activerecord` and
`rhosocial.activerecord.backend.impl.mariadb` are found under the same `rhosocial`
namespace after installation.

## Verify the installation

```python
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig

print(MariaDBBackend, MariaDBConnectionConfig)
```

Next: [Connection configuration](configuration.md).
