from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sistema.app.core.config import settings


def test_history_csv_migration_imports_csv_and_preserves_newer_user_state(tmp_path):
    db_path = tmp_path / "history_import.db"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    config = Config("alembic.ini")
    previous_database_url = settings.database_url
    settings.database_url = database_url

    try:
        command.upgrade(config, "0017_vehicles_user_transport")

        engine = sa.create_engine(database_url)
        newer_time = datetime(2026, 4, 18, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO users (
                        rfid,
                        chave,
                        nome,
                        projeto,
                        placa,
                        end_rua,
                        zip,
                        local,
                        checkin,
                        time,
                        last_active_at,
                        inactivity_days
                    ) VALUES (
                        :rfid,
                        :chave,
                        :nome,
                        :projeto,
                        :placa,
                        :end_rua,
                        :zip,
                        :local,
                        :checkin,
                        :time,
                        :last_active_at,
                        :inactivity_days
                    )
                    """
                ),
                {
                    "rfid": "CSV9001",
                    "chave": "CF10",
                    "nome": "Nome Antigo",
                    "projeto": "P83",
                    "placa": None,
                    "end_rua": None,
                    "zip": None,
                    "local": "main",
                    "checkin": 0,
                    "time": newer_time,
                    "last_active_at": newer_time,
                    "inactivity_days": 0,
                },
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            user_row = connection.execute(
                sa.text(
                    """
                    SELECT nome, projeto, cargo, email, local, checkin, time
                    FROM users
                    WHERE chave = 'CF10'
                    """
                )
            ).mappings().one()
            history_rows = connection.execute(
                sa.text(
                    """
                    SELECT atividade, projeto, informe, time
                    FROM checkinghistory
                    WHERE chave = 'CF10'
                    ORDER BY time
                    """
                )
            ).mappings().all()

        assert user_row["nome"] == "Adriano Jose da Silva"
        assert user_row["cargo"] == "PCR NS Engenharia de Processamento"
        assert user_row["email"] == "adjose@petrobras.com.br"
        assert user_row["projeto"] == "P83"
        assert user_row["local"] == "main"
        assert user_row["checkin"] in (0, False)
        assert str(user_row["time"]).startswith("2026-04-18 09:00:00")

        assert any(row["atividade"] == "check-in" and row["projeto"] == "P82" and row["informe"] == "normal" for row in history_rows)
        assert any(str(row["time"]).startswith("2026-04-18 09:00:00") and row["atividade"] == "check-out" for row in history_rows)
    finally:
        settings.database_url = previous_database_url
