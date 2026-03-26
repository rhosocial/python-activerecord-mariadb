-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/posts.sql
CREATE TABLE `posts` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`user_id` INT NOT NULL,
`title` VARCHAR(255) NOT NULL,
`content` TEXT,
`status` VARCHAR(50) NOT NULL DEFAULT 'published',
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
INDEX `idx_user_id` (`user_id`),
INDEX `idx_status` (`status`),
FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
