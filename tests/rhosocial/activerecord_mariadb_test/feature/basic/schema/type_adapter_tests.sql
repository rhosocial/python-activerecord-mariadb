-- tests/rhosocial/activerecord_mariadb_test/feature/basic/schema/type_adapter_tests.sql
CREATE TABLE IF NOT EXISTS type_adapter_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    optional_name VARCHAR(255),
    optional_age INT,
    last_login TEXT,
    is_premium BOOLEAN,
    unsupported_union VARCHAR(255),
    custom_bool VARCHAR(3),
    optional_custom_bool VARCHAR(3)
);
