# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/test_native_xml.py
"""MariaDB 11.8.9 has no ``XML`` column type.

The planned assertion is "``XML`` is carried as ``str`` and never parsed". That
requires a column type the server does not have: ``CREATE TABLE ... XML`` fails
with ``Unknown data type: 'XML' (errno: 4161, sqlstate: HY000)``. The test
therefore probes the capability and skips with the server's own message, so if
a future server (or a plugin) adds the type the same test starts asserting the
string form instead.
"""

import pytest


def test_xml_columns_are_carried_as_str(database):
    try:
        database.execute("CREATE TABLE native_xml (id INT PRIMARY KEY, doc XML)")
    except Exception as exc:  # the server has no such type; report exactly why
        pytest.skip(
            "MariaDB 11.8.9 server has no XML column type " f"(CREATE TABLE ... XML failed: {exc})"
        )

    try:
        database.execute("INSERT INTO native_xml (id, doc) VALUES (1, '<root><n>1</n></root>')")
        row = database.fetch_one(
            "SELECT doc, CAST(doc AS CHAR) AS txt FROM native_xml WHERE id = 1", ()
        )
        assert isinstance(row["doc"], str), "an XML column must surface as str"
        assert row["doc"] == "<root><n>1</n></root>"
        assert row["txt"] == "<root><n>1</n></root>"
    finally:
        database.execute("DROP TABLE IF EXISTS native_xml")
