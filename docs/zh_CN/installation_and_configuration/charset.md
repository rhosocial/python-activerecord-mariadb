# 字符集/编码

## 概述

MariaDB 使用字符集和排序规则来控制文本的存储和比较方式。MariaDB 后端的默认字符集是 `utf8mb4`，它支持完整的 Unicode 字符集（包括表情符号）。

## 配置

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

## 常用字符集

| 字符集 | 描述 | 推荐 |
|--------|------|------|
| `utf8mb4` | 完整 Unicode（4 字节） | 是 |
| `utf8` | 仅 BMP（3 字节） | 否（使用 utf8mb4） |
| `latin1` | 西欧语言 | 仅用于遗留系统 |

## 常用排序规则

| 排序规则 | 描述 |
|----------|------|
| `utf8mb4_unicode_ci` | Unicode，不区分大小写 |
| `utf8mb4_general_ci` | 更快但不太准确 |
| `utf8mb4_bin` | 二进制比较 |
| `utf8mb4_0900_ai_ci` | Unicode 9.0，不区分重音 |

## 最佳实践

1. **始终使用 `utf8mb4`** -- MariaDB 中的 `utf8` 仅支持 BMP 字符（3 字节）
2. **一般用例使用 `utf8mb4_unicode_ci`**
3. **需要区分大小写比较时使用 `utf8mb4_bin`**
4. **在连接和表级别都设置字符集**以保持一致性

AI Prompt: "MariaDB 中 utf8 和 utf8mb4 有什么区别？"
