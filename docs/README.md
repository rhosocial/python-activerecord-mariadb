<!-- docs/README.md -->
# rhosocial-activerecord MariaDB Backend Documentation

This directory contains documentation for the MariaDB backend implementation of
`rhosocial-activerecord`.

## Documentation Structure

- [English documentation](en_US/README.md)
- [Example scripts](examples/README.md)

## Overview

The documentation covers how to use the MariaDB backend with the core
`rhosocial-activerecord` package: connection and configuration, MariaDB-specific
features (types, dialect, storage engines, indexing, introspection, partitioning,
EXPLAIN, version gates), DDL, transactions, type adapters, testing, and
troubleshooting.

Backend documentation deliberately does **not** restate the framework manual.
Modeling, querying, relationships, and the expression system belong to the
[core library documentation](https://github.com/rhosocial/python-activerecord/tree/main/docs/en_US).
