# src/rhosocial/activerecord/backend/impl/mariadb/mixins/function.py
"""MariaDB SQL function support mixin."""
from typing import Dict


class MariaDBFunctionMixin:
    """MariaDB stored function DDL capability checks."""

    def supports_function(self) -> bool:
        return True

    def supports_create_function(self) -> bool:
        return True

    def supports_drop_function(self) -> bool:
        return True

    def supports_function_or_replace(self) -> bool:
        return True

    def supports_function_parameters(self) -> bool:
        return True

    _MARIADB_FUNCTION_VERSIONS = {
        # JSON functions: MariaDB 10.2.3+
        "json_extract": ((10, 2, 3), None),
        "json_unquote": ((10, 2, 3), None),
        "json_object": ((10, 2, 3), None),
        "json_array": ((10, 2, 3), None),
        "json_contains": ((10, 2, 3), None),
        "json_set": ((10, 2, 3), None),
        "json_remove": ((10, 2, 3), None),
        "json_type": ((10, 2, 3), None),
        "json_valid": ((10, 2, 3), None),
        "json_search": ((10, 2, 3), None),
        # Spatial functions: MariaDB 10.2+
        "st_geom_from_text": ((10, 2, 0), None),
        "st_geom_from_wkb": ((10, 2, 0), None),
        "st_as_text": ((10, 2, 0), None),
        "st_as_geojson": ((10, 2, 0), None),
        "st_distance": ((10, 2, 0), None),
        "st_within": ((10, 2, 0), None),
        "st_contains": ((10, 2, 0), None),
        "st_intersects": ((10, 2, 0), None),
        # Full-text search: All versions
        "match_against": (None, None),
        # SET type functions: All versions
        "find_in_set": (None, None),
        # Enum type functions: All versions
        "elt": (None, None),
        "field": (None, None),
        # Math enhanced functions: All versions
        "round_": (None, None),
        "pow": (None, None),
        "power": (None, None),
        "sqrt": (None, None),
        "mod": (None, None),
        "ceil": (None, None),
        "floor": (None, None),
        "trunc": (None, None),
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        # Bitwise functions: All versions (native operators)
        "bit_and": (None, None),
        "bit_or": (None, None),
        "bit_xor": (None, None),
        "bit_count": ((10, 0, 0), None),
        "bit_get_bit": (None, None),
        "bit_shift_left": (None, None),
        "bit_shift_right": (None, None),
        # Removed in MariaDB 13.0, which dropped the deprecated DES logic.
        # Declared with an upper bound so the gate is exercised and a future
        # caller cannot silently emit SQL that 13.0+ rejects.
        "des_encrypt": (None, (13, 0, 0)),
        "des_decrypt": (None, (13, 0, 0)),
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        This method combines:
        1. Core functions from rhosocial.activerecord.backend.expression.functions
        2. MariaDB-specific functions from rhosocial.activerecord.backend.impl.mariadb.functions
        """
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.mariadb import functions as mariadb_functions

        expression_constructors = {
            "xmlagg", "xmlattributes", "xmlcomment", "xmlconcat",
            "xmlelement", "xmlexists", "xmlforest", "xmlparse",
            "xmlpi", "xmlquery", "xmlroot", "xmlserialize", "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
                result[func_name] = True

        mariadb_funcs = getattr(mariadb_functions, "__all__", [])
        for func_name in mariadb_funcs:
            if func_name in self._MARIADB_FUNCTION_VERSIONS:
                result[func_name] = self._is_mariadb_function_supported(func_name)
            elif func_name not in result:
                result[func_name] = True

        return result

    def supports_function_name(self, name: str) -> bool:
        """Whether ``name`` exists as a SQL function on the configured version.

        Unlike :meth:`supports_functions`, which only reports what this
        backend can construct, this answers the question for an arbitrary
        name -- including functions that are *not* constructible here but
        whose availability is version-bounded, such as the DES functions
        removed in MariaDB 13.0.
        """
        if not isinstance(name, str):
            return False
        return self._is_mariadb_function_supported(name.strip().lower())

    def _is_mariadb_function_supported(self, func_name: str) -> bool:
        """Check if a MariaDB-specific function is supported based on version."""
        version_range = self._MARIADB_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True


__all__ = ['MariaDBFunctionMixin']
