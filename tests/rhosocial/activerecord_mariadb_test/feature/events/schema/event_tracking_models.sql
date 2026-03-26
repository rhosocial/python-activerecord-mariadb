-- tests/rhosocial/activerecord_mariadb_test/feature/events/schema/event_tracking_models.sql
CREATE TABLE `event_tracking_models` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`title` VARCHAR(255) NOT NULL,
`content` TEXT NOT NULL,
`view_count` INT NOT NULL DEFAULT 0,
`last_viewed_at` DATETIME(6) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
