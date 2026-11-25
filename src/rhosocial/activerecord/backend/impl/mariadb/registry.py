# src/rhosocial/activerecord/backend/impl/mariadb/registry.py
"""The MariaDB backend's expression registry.

MariaDB owns the kinds its own expression package declares -- the ones core
cannot name because they are MariaDB's spelling and not the standard's. It does
not own core's kinds and it does not list any other backend's: the overlap with
core is expressed by composition -- ``base=core_registry()`` -- and there is no
cross-backend merge anywhere.

The registry is built on first use, cached, and frozen. Freezing is what lets
the dialect hand the same table to every reader without one caller's
registration changing what another caller resolves.
"""

from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry
from rhosocial.activerecord.backend.expression.serialization import (
    core_registry,
    registry_for_packages,
)

#: The MariaDB backend's own expression package.
_MARIADB_EXPRESSION_PACKAGE = "rhosocial.activerecord.backend.impl.mariadb.expression"

_backend_registry = None


def backend_registry() -> ExpressionRegistry:
    """MariaDB's registry: core's kinds plus MariaDB's own, frozen and cached.

    The two owners are joined here and nowhere else. Core kinds are the
    overlap every backend shares; the rest are MariaDB's own, the ones its
    dialect renders and its artifacts may name.

    Returns:
        The frozen registry ``MariaDBDialect.artifact_registry()`` exposes.
    """
    global _backend_registry
    if _backend_registry is None:
        # Build into a local and publish only on success: a half-populated
        # instance cached under the module global would make every later call
        # fail with a confusing "no such kind" instead of the real cause.
        _backend_registry = registry_for_packages(
            _MARIADB_EXPRESSION_PACKAGE,
            base=core_registry(),
        )
    return _backend_registry
