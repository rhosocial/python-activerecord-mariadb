# Supported Versions

## MariaDB Version Support

| MariaDB Version | Support Status | Notes |
|-----------------|----------------|-------|
| 5.5.x | ❌ End of Life | No longer supported |
| 10.0.x | ❌ End of Life | No longer supported |
| 10.1.x | ❌ End of Life | No longer supported |
| 10.2.x | ✅ Supported | Adds window functions, CTE, JSON functions |
| 10.3.x | ✅ Recommended | Current LTS series, adds system-versioned tables, sequences |
| 10.4.x | ✅ Recommended | LTS series, adds `INSTEAD OF` triggers |
| 10.5.x | ✅ Recommended | LTS series, adds RETURNING clause |
| 10.6.x | ✅ Supported | LTS series, adds EXPLAIN ANALYZE |
| 10.11.x | ✅ Recommended | Current LTS, stable and widely deployed |
| 11.x | ✅ Supported | Innovation releases |
| 12.x | ✅ Supported | Latest innovation releases |

> **Important**: This backend is designed exclusively for MariaDB databases. The dialect behavior is tightly coupled with MariaDB version-specific features. **Do not use this backend with other MySQL-family databases** (including MySQL, Percona Server, or Aurora). While MariaDB shares MySQL compatibility, its dialect diverges in important ways (system-versioned tables, sequences, `RETURNING`, etc.). Using it with non-MariaDB databases may result in incorrect SQL generation or unexpected behavior.

## Version Feature Boundaries

The dialect auto-detects MariaDB features based on server version (`MARIADB_VERSION_BOUNDARIES`):

| Feature | Minimum Version |
|---------|-----------------|
| Window functions / CTE | 10.2.0 |
| JSON functions | 10.2.3 |
| JSON arrow operators (`->>`) | 10.2.7 |
| INTERSECT / EXCEPT | 10.3.0 |
| Sequences | 10.3.0 |
| System-versioned tables | 10.3.0 |
| `FOR UPDATE SKIP LOCKED` | 10.3.0 |
| RETURNING clause | 10.5.0 |
| EXPLAIN ANALYZE / FORMAT | 10.6.0 |
| `RENAME TABLE ... IF EXISTS` | 10.5.0 |

## Python Version Requirements

| Python Version | Support Status | Notes |
|----------------|----------------|-------|
| 3.8 | ✅ Supported | |
| 3.9 | ✅ Supported | |
| 3.10 | ✅ Supported | |
| 3.11 | ✅ Supported | |
| 3.12 | ✅ Supported | |
| 3.13 | ✅ Supported | Supports free-threaded build (3.13t) |
| 3.14 | ✅ Supported | Supports free-threaded build (3.14t) |

**Free-Threaded Python**: Starting from Python 3.13, a free-threaded (no-GIL) build is available as `python3.13t`, `python3.14t`, etc. This backend is compatible with free-threaded Python, though some threading-specific features may behave differently.

## Dependency Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| rhosocial-activerecord | >=1.0.0 | Core library |
| mariadb | >=2.0.0rc2 | MariaDB driver (only supported) |

⚠️ **Important**: This backend only supports the `mariadb` Python driver. Other drivers such as mysql-connector-python or PyMySQL are not supported.

💡 *AI Prompt:* "What is the difference between a MariaDB LTS release and an innovation release?"
