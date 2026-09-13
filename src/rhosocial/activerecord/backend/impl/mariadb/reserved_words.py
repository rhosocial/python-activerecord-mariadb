# src/rhosocial/activerecord/backend/impl/mariadb/reserved_words.py
"""
MariaDB reserved words list.

Source: MariaDB 11.0 Documentation (https://mariadb.com/kb/en/reserved-words/)
"""

MARIADB_RESERVED_WORDS = frozenset({
    "accessible", "add", "all", "alter", "analyze", "and", "as", "asc",
    "asensitive", "before", "between", "bigint", "binary", "blob", "both",
    "by", "call", "cascade", "case", "change", "char", "character", "check",
    "collate", "column", "condition", "constraint", "continue", "convert",
    "create", "cross", "current_date", "current_time", "current_timestamp",
    "current_user", "cursor", "database", "databases", "day_hour",
    "day_microsecond", "day_minute", "day_second", "dec", "decimal",
    "declare", "default", "delayed", "delete", "desc", "describe",
    "deterministic", "distinct", "distinctrow", "div", "double", "drop",
    "dual", "each", "else", "elseif", "enclosed", "escaped", "exists",
    "exit", "explain", "false", "fetch", "float", "float4", "float8",
    "for", "force", "foreign", "from", "fulltext", "generated", "get",
    "grant", "group", "having", "high_priority", "hour_microsecond",
    "hour_minute", "hour_second", "if", "ignore", "in", "index", "infile",
    "inner", "inout", "insensitive", "insert", "int", "int1", "int2",
    "int3", "int4", "int8", "integer", "interval", "into", "io_after_gts",
    "io_before_gts", "is", "iterate", "join", "key", "keys",
    "key_block_size", "kill", "leading", "leave", "left", "like", "limit",
    "linear", "lines", "load", "localtime", "localtimestamp", "lock",
    "long", "longblob", "longtext", "loop", "low_priority", "master_bind",
    "master_ssl_verify_server_cert", "match", "maxvalue", "mediumblob",
    "mediumint", "mediumtext", "middleint", "minute_microsecond",
    "minute_second", "mod", "modifies", "natural", "not",
    "no_write_to_binlog", "null", "numeric", "on", "optimize",
    "optimizer_costs", "option", "optionally", "or", "order", "out",
    "outer", "outfile", "partition", "precision", "primary", "procedure",
    "purge", "range", "read", "reads", "read_write", "real", "references",
    "regexp", "release", "rename", "repeat", "replace", "require",
    "resignal", "restrict", "return", "revoke", "right", "rlike",
    "row_count", "schema", "schemas", "second_microsecond", "select",
    "sensitive", "separator", "set", "show", "signal", "smallint",
    "spatial", "specific", "sql", "sql_after_gts", "sql_before_gts",
    "sqlexception", "sqlstate", "sqlwarning", "sql_big_result",
    "sql_calc_found_rows", "sql_small_result", "ssl", "starting", "stored",
    "straight_join", "table", "terminated", "then", "tinyblob", "tinyint",
    "tinytext", "to", "trailing", "trigger", "true", "undo", "union",
    "unique", "unlock", "unsigned", "update", "usage", "use", "using",
    "utc_date", "utc_time", "utc_timestamp", "values", "varbinary",
    "varchar", "varcharacter", "varying", "virtual", "when", "where",
    "while", "with", "write", "xor", "year_month", "zerofill",
})
