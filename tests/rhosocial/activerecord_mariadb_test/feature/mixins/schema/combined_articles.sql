-- tests/rhosocial/activerecord_mariadb_test/feature/mixins/schema/combined_articles.sql
CREATE TABLE `combined_articles` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`title` VARCHAR(255) NOT NULL,
`content` TEXT NOT NULL,
`status` VARCHAR(50) NOT NULL DEFAULT 'draft',
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
`version` INT NOT NULL DEFAULT 1,
`deleted_at` DATETIME(6) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
