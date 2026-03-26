-- tests/rhosocial/activerecord_mariadb_test/feature/events/schema/event_tests.sql
CREATE TABLE `event_tests` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`name` VARCHAR(255) NOT NULL,
`status` VARCHAR(50) NOT NULL DEFAULT 'draft',
`revision` INT NOT NULL DEFAULT 1,
`content` TEXT,
`created_at` DATETIME(6),
`updated_at` DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
