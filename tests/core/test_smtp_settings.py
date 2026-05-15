"""Tests for SMTP settings in sistema.app.core.config."""
import pytest
from pydantic_settings import BaseSettings


def test_smtp_defaults_to_disabled():
    """All SMTP settings have safe defaults; smtp_host is None (disabled)."""
    from sistema.app.core.config import Settings

    s = Settings()
    assert s.smtp_host is None
    assert s.smtp_user is None
    assert s.smtp_password is None
    assert s.smtp_from_email is None
    assert s.smtp_accident_notify_email is None
    # Numeric / bool defaults
    assert s.smtp_port == 587
    assert s.smtp_use_tls is False
    assert s.smtp_use_starttls is True
    assert s.smtp_timeout_seconds == 30
    assert s.smtp_max_retries == 3
    assert s.smtp_from_name == "CheckCheck"


def test_smtp_env_overrides(monkeypatch):
    """Env vars (uppercase) are read and override defaults correctly."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cr3t")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "Acme Corp")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_USE_STARTTLS", "false")
    monkeypatch.setenv("SMTP_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("SMTP_MAX_RETRIES", "5")
    monkeypatch.setenv("SMTP_ACCIDENT_NOTIFY_EMAIL", "admin@example.com")

    from sistema.app.core.config import Settings

    # Instantiate fresh so the monkeypatched env is picked up.
    # env_file is ignored when the key is already in the environment.
    s = Settings(_env_file=None)

    assert s.smtp_host == "smtp.example.com"
    assert s.smtp_port == 465
    assert s.smtp_user == "user@example.com"
    assert s.smtp_password == "s3cr3t"
    assert s.smtp_from_email == "noreply@example.com"
    assert s.smtp_from_name == "Acme Corp"
    assert s.smtp_use_tls is True
    assert s.smtp_use_starttls is False
    assert s.smtp_timeout_seconds == 60
    assert s.smtp_max_retries == 5
    assert s.smtp_accident_notify_email == "admin@example.com"
