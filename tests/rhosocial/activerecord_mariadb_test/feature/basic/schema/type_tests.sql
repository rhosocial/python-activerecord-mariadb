-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/type_tests.sql
CREATE TABLE `type_tests` (
    `id` CHAR(36) NOT NULL PRIMARY KEY,
    `string_field` VARCHAR(255) NOT NULL DEFAULT 'test string',
    `int_field` INT NOT NULL DEFAULT 42,
    `float_field` FLOAT NOT NULL DEFAULT 3.14,
    `decimal_field` DOUBLE NOT NULL DEFAULT 10.99,
    `bool_field` TINYINT NOT NULL DEFAULT 1,
    `datetime_field` TEXT NOT NULL,
    `json_field` JSON,
    `nullable_field` VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
