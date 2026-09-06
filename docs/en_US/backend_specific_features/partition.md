# Table Partitioning

## Overview

MariaDB supports table partitioning for large tables.

## Partitioning Strategies

| Strategy | Description | Minimum Version |
|----------|-------------|-----------------|
| RANGE | Range partitioning | 5.1+ |
| LIST | List partitioning | 5.1+ |
| HASH | Hash partitioning | 5.1+ |
| KEY | Key partitioning | 5.1+ |

## Creating Partitions

```sql
-- RANGE partitioning
CREATE TABLE orders (
    id INT,
    order_date DATE,
    amount DECIMAL(10,2)
) PARTITION BY RANGE (YEAR(order_date)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025)
);

-- LIST partitioning
CREATE TABLE users (
    id INT,
    region VARCHAR(20)
) PARTITION BY LIST COLUMNS(region) (
    PARTITION p_north VALUES IN ('north'),
    PARTITION p_south VALUES IN ('south'),
    PARTITION p_east VALUES IN ('east'),
    PARTITION p_west VALUES IN ('west')
);
```

## Partition Management

```sql
-- Add partition
ALTER TABLE orders ADD PARTITION (
    PARTITION p2025 VALUES LESS THAN (2026)
);

-- Drop partition
ALTER TABLE orders DROP PARTITION p2022;

-- Reorganize partition
ALTER TABLE orders REORGANIZE PARTITION p2023 INTO (
    PARTITION p2023_q1 VALUES LESS THAN ('2023-04-01'),
    PARTITION p2023_q2 VALUES LESS THAN ('2023-07-01')
);
```

## See Also

- [Performance](../troubleshooting/performance.md) — Query optimization

💡 *AI Prompt:* "When should I use partitioning in MariaDB?"
