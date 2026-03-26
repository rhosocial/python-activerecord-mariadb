-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/orders.sql
CREATE TABLE `orders` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`user_id` INT NOT NULL,
`order_number` VARCHAR(255) NOT NULL,
`total_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
`status` VARCHAR(50) NOT NULL DEFAULT 'pending',
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
INDEX `idx_user_id` (`user_id`),
FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
