-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/users.sql
CREATE TABLE `users` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`username` VARCHAR(191) NOT NULL UNIQUE,
`email` VARCHAR(191) NOT NULL UNIQUE,
`age` INT,
`balance` DOUBLE NOT NULL DEFAULT 0.0,
`is_active` TINYINT(1) NOT NULL DEFAULT 1,
`created_at` TEXT,
`updated_at` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
