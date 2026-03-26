-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/comments.sql
CREATE TABLE `comments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `post_ref` INT NOT NULL,
    `author` INT NOT NULL,
    `text` TEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL,
    `updated_at` DATETIME(6),
    `approved` TINYINT(1) DEFAULT 0,
    INDEX `idx_post_ref` (`post_ref`),
    INDEX `idx_author` (`author`),
    FOREIGN KEY (`post_ref`) REFERENCES `posts`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`author`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;