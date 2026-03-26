-- tests/rhosocial/activerecord_mariadb_test/feature/mixins/schema/timestamped_posts.sql
CREATE TABLE `timestamped_posts` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`title` VARCHAR(255) NOT NULL,
`content` TEXT NOT NULL,
`created_at` DATETIME(6),
`updated_at` DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
