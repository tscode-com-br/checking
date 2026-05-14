from sqlalchemy import text
from sqlalchemy.orm import Session


def next_accident_number(db: Session) -> int:
    """Devolve o próximo número sequencial (>=0). Primeiro acidente = 0."""
    row = db.execute(
        text("SELECT COALESCE(MAX(accident_number), -1) + 1 FROM accidents")
    ).scalar_one()
    return int(row)


def format_accident_number(number: int) -> str:
    """Formata como 4 dígitos zero-padded ('0000', '0001', ...)."""
    return f"{int(number):04d}"
