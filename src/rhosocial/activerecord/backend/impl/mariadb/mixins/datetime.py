# src/rhosocial/activerecord/backend/impl/mariadb/mixins/datetime.py
"""MariaDB DateTime formatting mixin.

MariaDB uses DATE_ADD/DATE_SUB/TIMESTAMPDIFF for datetime arithmetic.
"""
from typing import Any, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from .backend import MARIADB_VERSION_BOUNDARIES


class MariaDBDateTimeMixin:
    """MariaDB datetime formatting override.

    Provides MariaDB-specific date_trunc, interval, add/subtract and
    diff expressions using DATE_FORMAT, DATE_ADD, DATE_SUB and
    TIMESTAMPDIFF.
    """

    def format_date_trunc_expression(self, expr: "Any") -> Tuple[str, tuple]:
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value.upper()
        formats = {
            "YEAR": "%Y-01-01 00:00:00",
            "MONTH": "%Y-%m-01 00:00:00",
            "DAY": "%Y-%m-%d 00:00:00",
            "HOUR": "%Y-%m-%d %H:00:00",
            "MINUTE": "%Y-%m-%d %H:%i:00",
            "SECOND": "%Y-%m-%d %H:%i:%s",
        }
        if field not in formats:
            raise UnsupportedFeatureError(self.name, f"date_trunc({expr.field.value})")
        sql = f"CAST(DATE_FORMAT({source_sql}, {self.p()}) AS DATETIME)"
        return self.apply_alias(sql, source_params + (formats[field],), expr)

    def format_interval_expression(self, expr: "Any") -> Tuple[str, tuple]:
        sql = f"INTERVAL {self.p()} {expr.unit.value.upper()}"
        return self.apply_alias(sql, (expr.value,), expr)

    def format_datetime_add_expression(self, expr: "Any") -> Tuple[str, tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_ADD({source_sql}, {interval_sql})"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_subtract_expression(self, expr: "Any") -> Tuple[str, tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"DATE_SUB({source_sql}, {interval_sql})"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_diff_expression(self, expr: "Any") -> Tuple[str, tuple]:
        start_sql, start_params = expr.start.to_sql()
        end_sql, end_params = expr.end.to_sql()
        sql = f"TIMESTAMPDIFF({expr.unit.value.upper()}, {start_sql}, {end_sql})"
        return self.apply_alias(sql, start_params + end_params, expr)


__all__ = ['MariaDBDateTimeMixin']
