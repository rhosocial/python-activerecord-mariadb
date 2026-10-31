# src/rhosocial/activerecord/backend/impl/mariadb/mixins/function.py
"""MariaDB SQL function support mixin."""
from typing import Dict, Tuple


class MariaDBFunctionMixin:
    """MariaDB stored function DDL capability checks."""

    #: MariaDB reads ``||`` as logical OR unless the server runs with
    #: ``PIPES_AS_CONCAT``, so ``CONCAT`` is the only unconditional spelling.
    STRING_CONCATENATION = "CONCAT"


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
        # Math enhanced functions: all present in every version this backend
        # targets, except TRUNC -- measured across 10.2.44 through 13.1.1,
        # where it is absent on everything before 12.2 and present on 12.2,
        # 12.3, 13.0 and 13.1.
        "round_": (None, None),
        "pow": (None, None),
        "power": (None, None),
        "sqrt": (None, None),
        "mod": (None, None),
        "ceil": (None, None),
        "floor": (None, None),
        "trunc": ((12, 2, 0), None),
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
        """Check if a MariaDB-specific function is supported based on version.

        This is a capability check, so it answers before adaptation rather
        than raising: a name with no version bound is available on every
        server, and a version-bounded one is not claimed until a version is
        known.
        """
        version_range = self._MARIADB_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        version = self.version_or_none
        if version is None:
            return False

        min_version, max_version = version_range

        if min_version is not None and version < min_version:
            return False

        if max_version is not None and version > max_version:
            return False

        return True

    def format_char_length_function(self, expr) -> Tuple[str, tuple]:
        """Render the character length as ``CHAR_LENGTH(operand)``.

        The base spells this ``LENGTH``, and on MariaDB that answers a
        different question: measured on 13.1.1 (192.168.1.3:15694),
        ``LENGTH('héllo')`` is 6 -- the byte count, é being two bytes --
        while ``CHAR_LENGTH('héllo')`` is 5, the characters. The node's
        ``unit`` records the semantics the caller asked for and the core
        leaves the spelling to the backend, so the entry point is
        overridden rather than letting the standard spelling quietly count
        bytes where characters were meant. ``expr.unit`` is still not
        rendered: the unit is a semantic the node declares, and
        ``CHAR_LENGTH`` is this backend's one spelling for it.
        """
        operand_sql, operand_params = expr.operand.to_sql()
        sql = f"CHAR_LENGTH({operand_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(operand_params)


__all__ = ['MariaDBFunctionMixin']
