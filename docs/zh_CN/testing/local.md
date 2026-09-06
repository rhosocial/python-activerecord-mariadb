# 本地 MariaDB 测试

## 概述

本节介绍如何设置本地 MariaDB 测试环境。

## 使用 Docker 运行 MariaDB

```bash
# 运行 MariaDB 容器
docker run -d \
  --name mariadb-test \
  -e MARIADB_ROOT_PASSWORD=test \
  -e MARIADB_DATABASE=test \
  -p 3306:3306 \
  mariadb:10.11

# 等待 MariaDB 启动
docker exec mariadb-test mysqladmin ping -h localhost -u root -ptest --wait=30
```

## 使用 Docker Compose

```yaml
# docker-compose.yml
services:
  mariadb:
    image: mariadb:10.11
    environment:
      MARIADB_ROOT_PASSWORD: test
      MARIADB_DATABASE: test
    ports:
      - "3306:3306"
    volumes:
      - mariadb_data:/var/lib/mysql

volumes:
  mariadb_data:
```

```bash
docker-compose up -d
```

## 运行测试

```bash
# 设置环境变量
export MARIADB_HOST=localhost
export MARIADB_PORT=3306
export MARIADB_DATABASE=test
export MARIADB_USERNAME=root
export MARIADB_PASSWORD=test

# 运行测试
pytest tests/
```

## 字符集

MariaDB 连接默认使用 `utf8mb4`。创建测试数据库时，请确保字符集和排序规则与您的应用匹配：

```sql
CREATE DATABASE test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

💡 *AI 提示词：* "Docker 和 Docker Compose 之间有什么区别？"
