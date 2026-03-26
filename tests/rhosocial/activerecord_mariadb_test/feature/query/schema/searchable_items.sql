-- tests/rhosocial/activerecord_mariadb_test/feature/query/schema/searchable_items.sql
CREATE TABLE `searchable_items` (
`id` INT NOT NULL AUTO_INCREMENT,
`name` VARCHAR(255),
`tags` TEXT,
`created_at` DATETIME(6),
`updated_at` DATETIME(6),
PRIMARY KEY (`id`)
) ENGINE=InnoDB;
