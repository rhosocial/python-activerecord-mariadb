# Timezone Handling

## Overview

The MariaDB backend maintains the original form returned by the database without performing additional timezone conversions.

## Difference Between DATETIME and TIMESTAMP

MariaDB has two date/time types:

- **DATETIME**: Stores date/time without timezone information, similar to "calendar time"
- **TIMESTAMP**: Stores UTC timestamps; MariaDB automatically converts between the session timezone and UTC

```sql
-- Create table with specific types
CREATE TABLE events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    created_at DATETIME,      -- Without timezone
    updated_at TIMESTAMP      -- With timezone, auto-converts
);
```

## MariaDB Server Timezone

The MariaDB server's timezone settings affect how TIMESTAMP types are stored and retrieved:

```sql
-- View current timezone settings
SHOW VARIABLES LIKE 'time_zone';

-- Set session timezone
SET time_zone = '+08:00';
```

## Python Side Handling

It is recommended to use UTC or local timezone on the Python side:

```python
from datetime import datetime, timezone, timedelta


def to_utc(dt: datetime) -> datetime:
    """Convert to UTC time"""
    if dt.tzinfo is None:
        # Assume local timezone
        local_tz = datetime.now().astimezone().tzinfo
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Convert to local time"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_tz = datetime.now().astimezone().tzinfo
    return dt.astimezone(local_tz)
```

## Best Practices

1. **Store in UTC**: It is recommended to store UTC time in the database
2. **Convert at the frontend**: Perform timezone conversion at the application layer or frontend
3. **Avoid mixing**: Do not mix times from different timezones in the same system

```python
from datetime import datetime, timezone


class Event(ActiveRecord):
    name: str
    created_at: datetime

    @property
    def created_at_utc(self) -> datetime:
        if self.created_at.tzinfo is None:
            return self.created_at.replace(tzinfo=timezone.utc)
        return self.created_at.astimezone(timezone.utc)
```

## See Also

- [Type Mapping](mapping.md) — DATETIME / TIMESTAMP type mapping

💡 *AI Prompt:* "Why is it recommended to store time in UTC instead of local timezone?"
