-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/pydantic_validated_models.sql
-- MariaDB version of the pydantic_validated_models table schema

CREATE TABLE `pydantic_validated_models` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(32),
    `quantity` INT,
    `step_count` INT,
    `price` DECIMAL(10, 2),
    `start_at` DATETIME,
    `end_at` DATETIME,
    `status` VARCHAR(32),
    `normalized_name` VARCHAR(50),
    `created_token` VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
