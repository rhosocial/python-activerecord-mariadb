-- tests/rhosocial/activerecord_mariadb_test/feature/mixins/schema/tasks.sql
CREATE TABLE `tasks` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`title` VARCHAR(255) NOT NULL,
`is_completed` TINYINT(1) NOT NULL DEFAULT 0,
`deleted_at` TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
