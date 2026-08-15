# src/rhosocial/activerecord/backend/impl/mariadb/protocols/window_function.py
"""MariaDB Window Function protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MariaDBWindowFunctionSupport(Protocol):
    """MariaDB Window Function protocol.

    Feature Source: MariaDB 10.2+ (MySQL 8.0+)

    MariaDB Window Function features:
    - ROW_NUMBER(): Assign row numbers
    - RANK(): Rank rows with gaps
    - DENSE_RANK(): Rank rows without gaps
    - LEAD/LAG: Access other rows
    - FIRST_VALUE/LAST_VALUE: First/last values in frame
    - Aggregate functions with OVER clause

    Official Documentation:
    - https://mariadb.com/kb/en/window-functions/

    Version Requirements:
    - MariaDB 10.2+
    """

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported.

        MariaDB 10.2+ supports window functions.
        """
        ...

    def supports_named_windows(self) -> bool:
        """Whether named window definitions are supported.

        MariaDB 10.2+ supports named windows.
        """
        ...
