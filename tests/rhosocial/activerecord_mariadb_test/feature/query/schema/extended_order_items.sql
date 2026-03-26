-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/extended_order_items.sql
CREATE TABLE `extended_order_items` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`order_id` INT NOT NULL,
`product_name` VARCHAR(255) NOT NULL,
`quantity` INT NOT NULL DEFAULT 1,
`price` DECIMAL(10,2) NOT NULL,
`category` VARCHAR(255),
`region` VARCHAR(50),
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
INDEX `idx_order_id` (`order_id`),
FOREIGN KEY (`order_id`) REFERENCES `extended_orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
