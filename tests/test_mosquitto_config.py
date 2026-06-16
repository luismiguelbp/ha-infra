"""Structural tests for Mosquitto broker configuration and Compose alignment."""

from contract_helpers import (
    DOCKER_DIR,
    read_compose_host_ports,
    read_mosquitto_listeners,
    read_mosquitto_setting,
)


MOSQUITTO_CONF = DOCKER_DIR / "data" / "mosquitto" / "config" / "mosquitto.conf"
MOSQUITTO_COMPOSE = DOCKER_DIR / "compose-mosquitto.yml"


def test_mosquitto_compose_ports_match_active_listeners() -> None:
    """Published host ports match active mosquitto.conf listeners only."""
    listeners = {port for port, _protocol in read_mosquitto_listeners(MOSQUITTO_CONF)}
    published = set(read_compose_host_ports(MOSQUITTO_COMPOSE, "mosquitto"))

    assert published == listeners, (
        f"compose publishes {sorted(published)} but mosquitto listens on {sorted(listeners)}"
    )


def test_mosquitto_disallows_anonymous_access() -> None:
    """Production template requires authenticated clients."""
    assert read_mosquitto_setting(MOSQUITTO_CONF, "allow_anonymous") == "false"


def test_mosquitto_uses_password_file() -> None:
    """Authenticated broker references a password file."""
    assert read_mosquitto_setting(MOSQUITTO_CONF, "password_file") == (
        "/mosquitto/config/passwords_file"
    )


def test_mosquitto_healthcheck_uses_authenticated_sub() -> None:
    """Container healthcheck validates MQTT auth, not just TCP."""
    content = MOSQUITTO_COMPOSE.read_text()
    assert "mosquitto_sub" in content
    assert "MQTT_USER" in content
    assert "MQTT_PASSWORD" in content
    assert "$SYS/broker/uptime" in content
