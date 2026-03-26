-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/json_users.sql
CREATE TABLE `json_users` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`username` VARCHAR(255) NOT NULL,
`email` VARCHAR(255) NOT NULL,
`age` INT,
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
`settings` JSON,
`tags` JSON,
`profile` JSON,
`roles` JSON,
`scores` JSON,
`subscription` JSON,
`preferences` JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
