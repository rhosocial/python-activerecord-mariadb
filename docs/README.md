# rhosocial-activerecord-mariadb

MariaDB backend implementation for [rhosocial-activerecord](https://github.com/rhosocial/python-activerecord).

## Documentation / 文档

Please select your language / 请选择语言：

- [English Documentation](en_US/README.md)
- [中文文档 (Chinese)](zh_CN/README.md)

## Overview

The MariaDB backend brings the ActiveRecord pattern to MariaDB through the `mariadb`
driver. It builds on the MySQL backend and adds MariaDB-specific behaviour: `OR REPLACE`
on `CREATE TRIGGER`, `FOLLOWS` / `PRECEDES` trigger ordering, and `WAIT` / `NOWAIT` on
`ALTER TABLE`.

For the main ActiveRecord framework documentation, please visit the
[python-activerecord docs](https://github.com/rhosocial/python-activerecord/tree/docs/docs).