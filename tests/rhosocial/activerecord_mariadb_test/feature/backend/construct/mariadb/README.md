# MariaDB-specific construct tests

This directory is a namespace for backend-unique capability tests. It holds no
test files at this level: each leaf directory is one capability and may own
fixture/helper modules as well as tests.

These tests do not connect to a database, so no shard database is allocated.
