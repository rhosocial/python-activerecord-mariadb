# MariaDB-specific execution tests

This directory is a namespace for backend-unique execution capabilities. It
holds no test files at this level: each leaf directory is one capability and
owns its own shard `conftest.py`.

Every leaf is a separate shard database, numbered from `test_db_25` upward.
See `../../SHARDS.md` for the full directory-to-database map.
