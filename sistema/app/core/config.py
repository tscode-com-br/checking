from pydantic_settings import BaseSettings, SettingsConfigDict


TRANSPORT_AI_AGENT_MODES = ("agent", "deterministic")


def normalize_transport_ai_agent_mode(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return TRANSPORT_AI_AGENT_MODES[0]
    if normalized in TRANSPORT_AI_AGENT_MODES:
        return normalized
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "checking-sistema"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./checking.db"
    database_pool_size: int = 6
    database_max_overflow: int = 2
    database_pool_timeout_seconds: int = 5
    database_pool_recycle_seconds: int = 1800
    forms_url: str = (
        "https://forms.office.com/Pages/ResponsePage.aspx?id=QWJvW1ea5EuOUB36cueaV-4C0XpFTa1LmJM_FjZpp4pUOTFGR1QwSk00Vk5KQ0ExNUMzQldRSkpHWCQlQCN0PWcu&origin=QRCode"
    )
    tz_name: str = "Asia/Singapore"

    device_shared_key: str = "change-me"
    mobile_app_shared_key: str = "change-mobile-app-shared-key"
    provider_shared_key: str = "PETROBRASP80P82P83"
    admin_session_secret: str = "change-admin-session-secret"
    admin_session_max_age_seconds: int = 28800
    bootstrap_admin_key: str = "HR70"
    bootstrap_admin_name: str = "Tamer Salmem"
    bootstrap_admin_password: str = "eAcacdLe2"
    wifi_ssid: str = "TS 14 PRO"
    wifi_password: str = "00000000"

    heartbeat_seconds: int = 180
    forms_timeout_seconds: int = 30
    forms_max_retries: int = 3
    forms_queue_enabled: bool = True
    forms_worker_health_update_seconds: int = 5
    forms_worker_health_stale_seconds: int = 20
    forms_worker_unhealthy_consecutive_errors: int = 3
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-2025-08-07"
    openai_temperature: float | None = 0
    openai_timeout_seconds: int = 120
    openai_max_retries: int = 2
    mapbox_access_token: str | None = None
    mapbox_matrix_profile: str = "mapbox/driving-traffic"
    mapbox_directions_profile: str = "mapbox/driving-traffic"
    mapbox_timeout_seconds: int = 20
    mapbox_max_retries: int = 2
    mapbox_geocoding_permanent: bool = False
    here_api_key: str | None = None
    here_matrix_profile: str = "here/car-fast"
    here_directions_profile: str = "here/car-fast"
    here_timeout_seconds: int = 20
    here_max_retries: int = 2
    transport_ai_route_provider: str = "here"
    transport_ai_fake_matrix_asymmetric: bool = False
    transport_ai_enabled: bool = False
    transport_ai_agent_mode: str = "agent"
    transport_ai_settings_encryption_key: str | None = None
    transport_ai_operational_approval_evidence: str | None = None
    transport_ai_max_passengers_per_run: int = 80
    transport_ai_max_concurrent_runs: int = 1
    transport_ai_max_runtime_seconds: int = 180
    transport_ai_route_cache_ttl_seconds: int = 3600
    transport_ai_geocode_cache_ttl_days: int = 30
    event_archives_dir: str = "/app/data/event_archives"
    transport_exports_dir: str = "/app/data/transport_exports"
    serve_admin_site_in_api: bool = True
    serve_user_site_in_api: bool = True
    serve_transport_site_in_api: bool = True


settings = Settings()
