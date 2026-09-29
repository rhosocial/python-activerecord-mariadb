# tests/rhosocial/activerecord_mariadb_test/feature/backend/test_ssl_connection_params.py
"""Regression tests: MariaDB SSL/TLS config must reach the driver.

``MariaDBConnectionConfig`` inherits the generic ``SSLMixin``, so
``ssl_ca``/``ssl_cert``/``ssl_key``/``ssl_ciphers`` are collected. These tests
pin that ``get_connection_params()`` -- the single place both the sync and async
connect paths read from -- actually forwards them, instead of collecting them
and then dropping them.
"""

import pytest

from rhosocial.activerecord.backend.impl.mariadb.config import MariaDBConnectionConfig


def make_config(**kwargs):
    defaults = dict(
        host="db.example.com",
        port=3306,
        database="test_db",
        username="tester",
        password="secret",
    )
    defaults.update(kwargs)
    return MariaDBConnectionConfig(**defaults)


def test_ssl_is_requested_by_default():
    params = make_config().get_connection_params()
    assert params["ssl"] is True


def test_mutual_tls_certificates_are_forwarded():
    config = make_config(
        ssl_ca="/certs/ca.pem",
        ssl_cert="/certs/client.pem",
        ssl_key="/certs/client-key.pem",
    )
    params = config.get_connection_params()
    assert params["ssl_ca"] == "/certs/ca.pem"
    assert params["ssl_cert"] == "/certs/client.pem"
    assert params["ssl_key"] == "/certs/client-key.pem"


def test_ssl_ciphers_map_to_driver_ssl_cipher():
    """The driver spells the cipher list ``ssl_cipher``, not ``ssl_ciphers``."""
    params = make_config(ssl_ciphers="ECDHE-RSA-AES256-GCM-SHA384").get_connection_params()
    assert params["ssl_cipher"] == "ECDHE-RSA-AES256-GCM-SHA384"


def test_tls_version_and_verification_flags_are_forwarded():
    params = make_config(
        tls_version="TLSv1.3",
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    ).get_connection_params()
    assert params["tls_version"] == "TLSv1.3"
    assert params["ssl_verify_cert"] is True
    assert params["ssl_verify_identity"] is True


def test_unset_certificate_fields_are_omitted():
    """No ``ssl_ca=None``/``ssl_key=None`` noise: the driver must see "unset"."""
    params = make_config().get_connection_params()
    assert "ssl_ca" not in params
    assert "ssl_cert" not in params
    assert "ssl_key" not in params
    assert "ssl_cipher" not in params


def test_ssl_disabled_suppresses_all_tls_material():
    """``ssl_disabled=True`` must win over any certificate material supplied."""
    params = make_config(
        ssl_disabled=True,
        ssl_ca="/certs/ca.pem",
        ssl_cert="/certs/client.pem",
        ssl_key="/certs/client-key.pem",
        ssl_ciphers="ECDHE-RSA-AES256-GCM-SHA384",
    ).get_connection_params()
    assert "ssl" not in params
    for key in ("ssl_ca", "ssl_cert", "ssl_key", "ssl_cipher", "tls_version"):
        assert key not in params


def test_certificate_only_setup_still_enables_tls():
    """Supplying just a CA is the common server-verified setup."""
    params = make_config(ssl_ca="/certs/ca.pem").get_connection_params()
    assert params["ssl"] is True
    assert params["ssl_ca"] == "/certs/ca.pem"


def test_client_cert_without_key_is_still_reported_to_the_driver():
    """The driver owns this check; the config must not swallow the mismatch."""
    params = make_config(ssl_cert="/certs/client.pem").get_connection_params()
    assert params["ssl_cert"] == "/certs/client.pem"
    assert "ssl_key" not in params


@pytest.mark.parametrize(
    "env,expected",
    [
        ("MARIADB_SSL_CA", "ssl_ca"),
        ("MARIADB_SSL_CERT", "ssl_cert"),
        ("MARIADB_SSL_KEY", "ssl_key"),
        ("MARIADB_SSL_CIPHERS", "ssl_ciphers"),
    ],
)
def test_from_env_reads_certificate_material(monkeypatch, env, expected):
    monkeypatch.setenv(env, "/from/env.pem")
    config = MariaDBConnectionConfig.from_env()
    assert getattr(config, expected) == "/from/env.pem"
