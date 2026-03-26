-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/posts.sql
CREATE TABLE `posts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `author` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `content` TEXT,
    `published_at` DATETIME(6),
    `published` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME(6),
    `updated_at` DATETIME(6),
    INDEX `idx_author` (`author`),
    FOREIGN KEY (`author`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;