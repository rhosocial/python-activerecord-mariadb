<!-- docs/en_US/troubleshooting/connection.md -->
# Connection errors

## TLS handshake failures

`ssl_disabled` defaults to `False`, so the backend asks for TLS on every
connection. If the server has no TLS configured, either enable it on the server
or set `ssl_disabled=True` explicitly.

```python
config = MariaDBConnectionConfig(
    host="localhost", database="myapp", username="app", password="secret",
    ssl_disabled=True,
)
```

When the server does have TLS but rejects the handshake, check the hostname in
the certificate against `ssl_verify_identity`, the CA in `ssl_ca`, and the
`tls_version` floor. For mutual TLS, all of `ssl_ca`, `ssl_cert` and `ssl_key`
must be present and readable by the process.

## Authentication failures

- `Access denied for user` — verify the user/host pair (`'app'@'localhost'` and
  `'app'@'%'` are different accounts) and the database grants.
- `Unknown database` — the `database` field must name an existing database;
  this backend does not create one.
- `Plugin ... not loaded` — the server may require a different auth plugin than
  the connector supports; update the connector.

## Charset mismatches

Garbled text usually means the database, table and connection disagree.
`charset` becomes `SET NAMES <charset>` in the driver's `init_command`; verify
the server's defaults with `get_database_info()` and the column's effective
charset with `list_columns()`. Use `utf8mb4`, not the `utf8` alias — see
[Character set & collation](../installation_and_configuration/charset.md).

## Lazy reconnects

The backend reconnects on use and after a failed statement. A reconnect ends the
current transaction and discards savepoints. If a failure appears "retried"
without your code asking for it, check whether the statement was reissued on a
new connection; see
[Connection management](../installation_and_configuration/pool.md).

## Version-related rejects

`errno 1064` (syntax error) on an older server often means a feature gate
resolved optimistically for a newer version. Call
`backend.introspect_and_adapt()` before gating and check the relevant floor in
[Version gates](../mariadb_specific_features/version_gates.md).

## Network and sockets

- A host of `localhost` may use a Unix socket; use `127.0.0.1` to force TCP.
- With PowerShell 7, proxy variables are not inherited from the system. For
  package installs or remote test servers behind a proxy, inject
  `HTTP_PROXY`/`HTTPS_PROXY` into the command that needs them and keep
  `NO_PROXY=127.0.0.1,localhost,::1` for local servers.
