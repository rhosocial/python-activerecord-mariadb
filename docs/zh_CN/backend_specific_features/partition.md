# 表分区

## 概述

MariaDB 支持表分区用于大表。

## 分区策略

| 策略 | 说明 | 最低版本 |
|------|------|---------|
| RANGE | 范围分区 | 5.1+ |
| LIST | 列表分区 | 5.1+ |
| HASH | 哈希分区 | 5.1+ |
| KEY | 键分区 | 5.1+ |

## 创建分区

```sql
-- RANGE 分区
CREATE TABLE orders (
    id INT,
    order_date DATE,
    amount DECIMAL(10,2)
) PARTITION BY RANGE (YEAR(order_date)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025)
);

-- LIST 分区
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

## 分区管理

```sql
-- 添加分区
ALTER TABLE orders ADD PARTITION (
    PARTITION p2025 VALUES LESS THAN (2026)
);

-- 删除分区
ALTER TABLE orders DROP PARTITION p2022;

-- 重组分区
ALTER TABLE orders REORGANIZE PARTITION p2023 INTO (
    PARTITION p2023_q1 VALUES LESS THAN ('2023-04-01'),
    PARTITION p2023_q2 VALUES LESS THAN ('2023-07-01')
);
```

## 另请参阅

- [性能](../troubleshooting/performance.md) — 查询优化

💡 *AI 提示：* "何时应该在 MariaDB 中使用分区？"
