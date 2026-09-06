# Local MariaDB Testing

## Overview

This section describes how to set up a local MariaDB testing environment.

## Running MariaDB with Docker

```bash
# Run MariaDB container
docker run -d \
  --name mariadb-test \
  -e MARIADB_ROOT_PASSWORD=test \
  -e MARIADB_DATABASE=test \
  -p 3306:3306 \
  mariadb:10.11

# Wait for MariaDB to start
docker exec mariadb-test mysqladmin ping -h localhost -u root -ptest --wait=30
```

## Using Docker Compose

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

## Running Tests

```bash
# Set environment variables
export MARIADB_HOST=localhost
export MARIADB_PORT=3306
export MARIADB_DATABASE=test
export MARIADB_USERNAME=root
export MARIADB_PASSWORD=test

# Run tests
pytest tests/
```

## Character Set

MariaDB defaults to `utf8mb4` for the connection. When creating a test database, ensure the character set and collation match your application:

```sql
CREATE DATABASE test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

💡 *AI Prompt:* "What is the difference between Docker and Docker Compose?"
