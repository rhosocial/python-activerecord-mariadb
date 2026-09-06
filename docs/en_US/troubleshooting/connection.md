# Common Connection Errors

## Overview

This section covers common MariaDB connection errors and their solutions.

## Connection Refused

### Error Message
```
ERROR 2003 (HY000): Can't connect to MariaDB server
```

### Causes
- MariaDB service is not running
- Incorrect port
- Firewall blocking

### Solutions
```bash
# Check if MariaDB is running
sudo systemctl status mariadb

# Check port
telnet localhost 3306
```

## Authentication Failed

### Error Message
```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

### Causes
- Incorrect username or password
- User does not have remote access permissions

### Solutions
```sql
-- Execute on MariaDB server
CREATE USER 'user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON database.* TO 'user'@'%';
FLUSH PRIVILEGES;
```

## Connection Timeout

### Error Message
```
ERROR 2003: Can't connect to MariaDB server (110)
```

### Causes
- Network issues
- connect_timeout setting is too short

### Solutions
```python
config = MariaDBConnectionConfig(
    host='remote.host.com',
    connect_timeout=30,  # Increase timeout
)
```

## Connection Loss and Automatic Recovery

In long-running applications, database connections may be dropped for various reasons. The MariaDB backend implements automatic recovery when connections are lost.

### Common Connection Loss Scenarios

| Scenario | Cause | Error Codes |
|----------|-------|-------------|
| `wait_timeout` expiry | Connection idle time exceeds `wait_timeout` | 2006, 2013 |
| Connection killed | DBA executes `KILL CONNECTION` | 2013 |
| Network instability | TCP connection drops | 2003, 2055 |
| Server restart | MariaDB restart or crash | 2006, 2013 |
| Firewall timeout | Firewall closes long-idle TCP connections | 2013 |

### Automatic Recovery

The backend checks connection status before each query and reconnects transparently when lost. On query failure due to a connection error, it retries automatically (max 2 retries), only retrying on connection errors and raising others directly.

### Manual Keep-Alive

For proactive connection maintenance, use the `ping()` method:

```python
# Check connection status without auto-reconnect
is_alive = backend.ping(reconnect=False)

# Check connection status with auto-reconnect if disconnected
is_alive = backend.ping(reconnect=True)
```

### Async Backend Support

The async backend (`AsyncMariaDBBackend`) provides the same recovery mechanism:

```python
# Async ping
is_alive = await async_backend.ping(reconnect=True)

# Async queries also auto-reconnect
result = await async_backend.execute("SELECT 1")
```

### Best Practices

1. **Configure MariaDB timeouts appropriately**:

```sql
-- View current settings
SHOW VARIABLES LIKE 'wait_timeout';
SHOW VARIABLES LIKE 'interactive_timeout';

-- Recommended settings (adjust as needed)
SET GLOBAL wait_timeout = 28800;        -- 8 hours
SET GLOBAL interactive_timeout = 28800; -- 8 hours
```

2. **Multi-process worker scenarios**: Each worker process should have its own backend instance. The `mariadb` driver is `threadsafety=1`, so never share a connection across threads.

```python
def worker_process(worker_id, config):
    # Create independent backend instance within the process
    backend = MariaDBBackend(connection_config=config)
    backend.connect()
    try:
        do_work(backend)
    finally:
        backend.disconnect()
```

### Connection Error Codes Reference

| Error Code | Name | Description |
|------------|------|-------------|
| 2003 | CR_CONN_HOST_ERROR | Can't connect to MariaDB server |
| 2006 | CR_SERVER_GONE_ERROR | MariaDB server has gone away |
| 2013 | CR_SERVER_LOST | Lost connection during query |
| 2055 | CR_SERVER_LOST_EXTENDED | Extended connection lost |

💡 *AI Prompt:* "How to troubleshoot MariaDB connection errors? How does the backend automatically recover connections?"
