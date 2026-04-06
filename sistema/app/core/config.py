from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "checking-sistema"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./checking.db"
    forms_url: str = (
        "https://forms.office.com/Pages/ResponsePage.aspx?id=QWJvW1ea5EuOUB36cueaV-4C0XpFTa1LmJM_FjZpp4pUOTFGR1QwSk00Vk5KQ0ExNUMzQldRSkpHWCQlQCN0PWcu&origin=QRCode"
    )
    tz_name: str = "Asia/Singapore"

    device_shared_key: str = "change-me"
    mobile_app_shared_key: str = "change-mobile-app-shared-key"
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
    event_archives_dir: str = "/app/data/event_archives"


settings = Settings()
