# tests/rhosocial/activerecord_mariadb_test/feature/backend/adapters/native/native_capabilities.py
"""Native-type capability gates for the native-type tests.

Every probe answers "what does this server have", never "does MariaDB support
this": each one is the backend dialect's own capability report (the same gate
the corresponding type formatter enforces), so a missing capability is an
environment fact and the skip reason says which probe answered ``no`` -- the
capability rule the testing plan §4.1 states for these families.

The version boundary a probe encodes belongs to the dialect alone
(``MARIADB_VERSION_BOUNDARIES``): restating it here would make the test tree a
second authority on what a server can do, and a version number in a skip
reason would report the mechanism instead of the answer.
"""


def supports_uuid(dialect) -> bool:
    """Whether the server has the native ``UUID`` column type.

    Asks the dialect's own capability report, which is the same gate the
    ``UUID`` type's formatter enforces; a dialect that cannot name its version
    answers no.
    """
    return bool(dialect.supports_data_type_mariadb_uuid())


def uuid_skip_reason(dialect) -> str:
    """A skip reason that names the probe that answered ``no``.

    The probe is the decision, so it is the fact worth reporting: naming the
    dialect and the probe tells the reader which question was asked of this
    server and where the answer came from, without the test tree repeating the
    version boundary the dialect already owns.
    """
    return (
        f"environment: {type(dialect).__name__} reports no native UUID column "
        f"type (supports_data_type_mariadb_uuid() -> False)"
    )


def supports_json_type_validation(dialect) -> bool:
    """Whether a ``JSON`` column refuses a document that is not valid JSON."""
    return bool(dialect.supports_json_type_validation())


def json_type_validation_skip_reason(dialect) -> str:
    """A skip reason that names the probe that answered ``no``."""
    return (
        f"environment: {type(dialect).__name__} stores JSON as an unvalidated "
        f"LONGTEXT alias on this server (supports_json_type_validation() -> False)"
    )
