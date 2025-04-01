# rhosocial ActiveRecord MariaDB Backend

[![PyPI version](https://badge.fury.io/py/rhosocial-activerecord-mariadb.svg)](https://badge.fury.io/py/rhosocial-activerecord-mariadb)
[![Python](https://img.shields.io/pypi/pyversions/rhosocial-activerecord-mariadb.svg)](https://pypi.org/project/rhosocial-activerecord-mariadb/)
[![Tests](https://github.com/rhosocial/python-activerecord-mariadb/actions/workflows/test.yml/badge.svg)](https://github.com/rhosocial/python-activerecord-mariadb/actions)
[![Coverage Status](https://codecov.io/gh/rhosocial/python-activerecord-mariadb/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rhosocial/python-activerecord-mariadb/tree/main)
[![License](https://img.shields.io/github/license/rhosocial/python-activerecord-mariadb.svg)](https://github.com/rhosocial/python-activerecord-mariadb/blob/main/LICENSE)
[![Powered by vistart](https://img.shields.io/badge/Powered_by-vistart-blue.svg)](https://github.com/vistart)

<div align="center">
    <img src="https://raw.githubusercontent.com/rhosocial/python-activerecord/main/docs/images/logo.svg" alt="rhosocial ActiveRecord Logo" width="200"/>
    <p>MariaDB backend implementation for rhosocial-activerecord, providing a robust and optimized MariaDB database support.</p>
</div>

## Overview

This package provides MariaDB backend support for the [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord) ORM framework. It enables seamless integration with MariaDB databases while leveraging all the features of the ActiveRecord pattern implementation.

## Features

> This project is still under development and features are subject to change. Please stay tuned for the latest changes.

- 🚀 Optimized MariaDB-specific query generation
- 🔒 Full support for MariaDB's unique features
- 📦 Connection pooling support (optional)
- 🔄 Comprehensive transaction management
- 🔍 Advanced query capabilities specific to MariaDB
- 🔌 Simple configuration and setup

## Requirements

- Python 3.8+
- rhosocial-activerecord 1.0.0+
- mariadb 1.1.0+

## Installation

```bash
# Basic installation
pip install rhosocial-activerecord-mariadb

# With connection pooling support
pip install rhosocial-activerecord-mariadb[pooling]

# With development tools
pip install rhosocial-activerecord-mariadb[dev]
```

## Usage

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.mariadb.backend import MariaDBBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime
    deleted_at: Optional[datetime] = None

# Configure with MariaDB backend
User.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='myapp',
        user='dbuser',
        password='dbpassword'
    ),
    backend_class=MariaDBBackend
)

# Create a table (if not exists)
User.create_table_if_not_exists()

# Create a new user
user = User(name='John Doe', email='john@example.com', created_at=datetime.now())
user.save()

# Query users
active_users = User.query() \
    .where('deleted_at IS NULL') \
    .order_by('created_at DESC') \
    .all()

# Update user
user.name = 'Jane Doe'
user.save()

# Delete user (soft delete if implemented)
user.delete()
```

## Advanced MariaDB Features

This backend supports MariaDB-specific features and optimizations:

```python
# Using MariaDB fulltext search
results = User.query() \
    .where('MATCH(name, email) AGAINST(? IN BOOLEAN MODE)', ('+John -Doe', )) \
    .all()

# Using MariaDB JSON operations
results = User.query() \
    .where('JSON_EXTRACT(settings, "$.notifications") = ?', ('enabled', )) \
    .all()

# Batch insert with ON DUPLICATE KEY UPDATE
User.batch_insert_or_update([user1, user2, user3])
```

## Documentation

Complete documentation is available at [python-activerecord MariaDB Backend](https://docs.python-activerecord.dev.rho.social/backends/mariadb.html)

## Contributing

We welcome and value all forms of contributions! For details on how to contribute, please see our [Contributing Guide](https://github.com/rhosocial/python-activerecord-mariadb/blob/main/CONTRIBUTING.md).

## License

[![license](https://img.shields.io/github/license/rhosocial/python-activerecord-mariadb.svg)](https://github.com/rhosocial/python-activerecord-mariadb/blob/main/LICENSE)

Copyright © 2025 [vistart](https://github.com/vistart)