# src/rhosocial/activerecord/backend/impl/mariadb/config.py
"""MariaDB connection configuration."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from rhosocial.activerecord.backend.config import (
    BaseConfig,
    BasicConnectionMixin,
    ConnectionPoolMixin,
    SSLMixin,
    CharsetMixin,
    TimezoneMixin,
    VersionMixin,
    LoggingMixin,
)


@dataclass
class MariaDBConnectionConfig(
    BaseConfig,
    BasicConnectionMixin,
    ConnectionPoolMixin,
    SSLMixin,
    CharsetMixin,
    TimezoneMixin,
    VersionMixin,
    LoggingMixin,
):
    """MariaDB connection configuration.

    This class extends the base configuration with MariaDB-specific options.
    """

    autocommit: bool = False
    ssl_disabled: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = super().to_dict()
        result["autocommit"] = self.autocommit
        result["ssl_disabled"] = self.ssl_disabled
        return result

    @classmethod
    def from_env(cls, prefix: str = "MARIADB_") -> "MariaDBConnectionConfig":
        """Create configuration from environment variables.

        Args:
            prefix: Environment variable prefix (default: 'MARIADB_')

        Returns:
            MariaDBConnectionConfig instance
        """
        import os

        env_values = {}

        mapping = {
            "HOST": "host",
            "PORT": "port",
            "DATABASE": "database",
            "USERNAME": "username",
            "PASSWORD": "password",
            "CHARSET": "charset",
            "COLLATION": "collation",
            "POOL_SIZE": "pool_size",
            "POOL_TIMEOUT": "pool_timeout",
            "AUTOCOMMIT": "autocommit",
            "SSL_DISABLED": "ssl_disabled",
        }

        for env_key, config_key in mapping.items():
            full_key = f"{prefix}{env_key}"
            if full_key in os.environ:
                value = os.environ[full_key]
                if config_key == "port":
                    value = int(value)
                elif config_key == "pool_size":
                    value = int(value)
                elif config_key == "pool_timeout":
                    value = int(value)
                elif config_key == "autocommit":
                    value = value.lower() in ("true", "yes", "1", "on")
                elif config_key == "ssl_disabled":
                    value = value.lower() in ("true", "yes", "1", "on")
                env_values[config_key] = value

        return cls(**env_values)
