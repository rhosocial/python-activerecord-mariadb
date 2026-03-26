-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/type_cases.sql
CREATE TABLE `type_cases` (
    `id` CHAR(36) NOT NULL PRIMARY KEY,
    `username` TEXT NOT NULL,
    `email` TEXT NOT NULL,
    `tiny_int` TEXT,
    `small_int` TEXT,
    `big_int` TEXT,
    `float_val` TEXT,
    `double_val` TEXT,
    `decimal_val` TEXT,
    `char_val` TEXT,
    `varchar_val` TEXT,
    `text_val` TEXT,
    `date_val` TEXT,
    `time_val` TEXT,
    `timestamp_val` TEXT,
    `blob_val` TEXT,
    `json_val` TEXT,
    `array_val` TEXT,
    `is_active` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
