-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/nodes.sql
CREATE TABLE `nodes` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`name` VARCHAR(255) NOT NULL,
`parent_id` INT NULL,
`value` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
INDEX `idx_parent_id` (`parent_id`),
FOREIGN KEY (`parent_id`) REFERENCES `nodes`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
