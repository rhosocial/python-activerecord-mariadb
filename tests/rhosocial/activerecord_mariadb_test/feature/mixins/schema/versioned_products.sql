-- tests/rhosocial/activerecord_mariadb_test/feature/mixins/schema/versioned_products.sql
CREATE TABLE `versioned_products` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`name` VARCHAR(255) NOT NULL,
`price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
`version` INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
