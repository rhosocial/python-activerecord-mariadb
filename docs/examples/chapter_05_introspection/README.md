<!-- docs/examples/chapter_05_introspection/README.md -->
# Chapter 5 — Introspection

`introspection.py` walks the three layers this backend answers: what the
database declares (schema), what it has been doing (operational facts), and what
its rows hold (data families). It also calls the MariaDB-only families
(`table-options`, `sequences`, `partitions`, `routines`, `constraints`).

## Run

```powershell
$env:MARIADB_HOST='127.0.0.1'; $env:MARIADB_DATABASE='test_db'
$env:MARIADB_USERNAME='app'; $env:MARIADB_PASSWORD='secret'
python docs/examples/chapter_05_introspection/introspection.py
```

The script is read-only and needs no table of its own; point it at any database
the user can read.

## What to look for

- `backend.introspect_and_adapt()` makes version-gated probes answer for the
  connected server before any probe is queried.
- `backend.dialect.supports_*()` exposes each capability probe.
- `SHOW`-style passthroughs (`introspector.show`) are library-only and are not
  offered through the CLI introspect vocabulary.
- A `False` probe means the question cannot be asked of this server, not that
  the answer was empty.
