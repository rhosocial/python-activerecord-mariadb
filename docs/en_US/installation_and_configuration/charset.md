# Character Set / Encoding

## Overview

MariaDB uses character sets and collations to control how text is stored and compared. The default character set for the MariaDB backend is `utf8mb4`, which supports the full Unicode character set including emojis.

## Configuration

```python
config = MariaDBConnectionConfig(
    host='localhost',
    port=3306,
    database='myapp',
    username='user',
    password='password',
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci',
)
```

## Common Character Sets

| Character Set | Description | Recommended |
|--------------|-------------|-------------|
| `utf8mb4` | Full Unicode (4 bytes) | Yes |
| `utf8` | BMP only (3 bytes) | No (use utf8mb4) |
| `latin1` | Western European | Legacy only |

## Common Collations

| Collation | Description |
|-----------|-------------|
| `utf8mb4_unicode_ci` | Unicode, case-insensitive |
| `utf8mb4_general_ci` | Faster but less accurate |
| `utf8mb4_bin` | Binary comparison |
| `utf8mb4_0900_ai_ci` | Unicode 9.0, accent-insensitive |

## Best Practices

1. **Always use `utf8mb4`** -- `utf8` in MariaDB only supports BMP characters (3 bytes)
2. **Use `utf8mb4_unicode_ci`** for general use cases
3. **Use `utf8mb4_bin`** when you need case-sensitive comparisons
4. **Set charset at both connection and table level** for consistency

AI Prompt: "What is the difference between utf8 and utf8mb4 in MariaDB?"
