-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/column_mapping_items.sql
CREATE TABLE `column_mapping_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `item_total` INT NOT NULL,
    `remarks` INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;