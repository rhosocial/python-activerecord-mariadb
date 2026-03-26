-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/comments.sql
CREATE TABLE `comments` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`user_id` INT NOT NULL,
`post_id` INT NOT NULL,
`content` TEXT,
`is_hidden` BOOLEAN DEFAULT FALSE,
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
INDEX `idx_user_id` (`user_id`),
INDEX `idx_post_id` (`post_id`),
FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
FOREIGN KEY (`post_id`) REFERENCES `posts`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
