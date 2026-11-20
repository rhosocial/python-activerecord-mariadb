# src/rhosocial/activerecord/backend/impl/mariadb/protocols/server_parameters.py
"""MariaDB server / session parameter support protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MariaDBServerParametersSupport(Protocol):
    """The server and session parameters MariaDB reports about itself.

    These are not capabilities: an operator can change them, so no version
    decides them. The backend reads the whole set once during adaptation
    (``SHOW SESSION VARIABLES``) and records it on the dialect; this protocol is
    how a caller asks what the server is actually doing rather than what it
    might do.

    Values are MariaDB's own spellings (``ON`` / ``OFF`` / strings). A variable
    the server did not report is absent from the record, never invented.
    """

    def server_parameters(self) -> dict:
        """Every recorded value, keyed by its MariaDB variable name."""
        ...

    def explicit_defaults_for_timestamp(self) -> bool:
        """Whether TIMESTAMP columns hold only what a statement wrote.

        ``False`` means the table's first TIMESTAMP column carries an implicit
        ``DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP``, so an UPDATE
        rewrites a column it never names.
        """
        ...
