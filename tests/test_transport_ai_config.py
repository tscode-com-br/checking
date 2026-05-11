import os
import subprocess
import sys
import textwrap
from pathlib import Path

from sistema.app.core.config import Settings


def test_transport_ai_settings_default_to_safe_server_side_values():
    settings = Settings(_env_file=None)

    assert settings.transport_ai_enabled is False
    assert settings.transport_ai_agent_mode == "agent"
    assert settings.transport_ai_operational_approval_evidence is None
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-5-2025-08-07"
    assert settings.openai_temperature == 0
    assert settings.openai_timeout_seconds == 120
    assert settings.openai_max_retries == 2
    assert settings.here_api_key is None
    assert settings.here_matrix_profile == "here/car-fast"
    assert settings.here_directions_profile == "here/car-fast"
    assert settings.here_timeout_seconds == 20
    assert settings.here_max_retries == 2
    assert settings.transport_ai_route_provider == "here"
    assert settings.transport_ai_fake_matrix_asymmetric is False
    assert settings.transport_ai_max_passengers_per_run == 80
    assert settings.transport_ai_max_concurrent_runs == 1
    assert settings.transport_ai_max_runtime_seconds == 180
    assert settings.transport_ai_route_cache_ttl_seconds == 3600
    assert settings.transport_ai_geocode_cache_ttl_days == 30


def test_app_boots_without_ai_keys_when_transport_ai_is_disabled(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(repo_root),
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'transport_ai_disabled.db').as_posix()}",
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "provider-test-key",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": "HR70",
            "BOOTSTRAP_ADMIN_NAME": "Config Test Admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "test-bootstrap-admin-password",
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_EXPORTS_DIR": str(tmp_path / "transport_exports"),
            "TRANSPORT_AI_ENABLED": "false",
        }
    )
    env.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                from fastapi.testclient import TestClient
                from sistema.app.main import app

                with TestClient(app) as client:
                    response = client.get('/api/health')
                    assert response.status_code == 200

                print('transport-ai-disabled-ok')
                """
            ),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-disabled-ok" in result.stdout