"""Tests for Modo Acidente Pydantic schemas (Task A2)."""
import pytest
from pydantic import ValidationError

from sistema.app.schemas import (
    AccidentSummary,
    AdminAccidentOpenRequest,
    SituacaoPessoalRow,
    WebAccidentOpenRequest,
)


# ---------------------------------------------------------------------------
# AdminAccidentOpenRequest
# ---------------------------------------------------------------------------


def test_admin_open_request_requires_location_or_custom():
    """Neither location_id nor custom_location_name → ValidationError."""
    with pytest.raises(ValidationError):
        AdminAccidentOpenRequest(project_id=1)


def test_admin_open_request_rejects_both_location_and_custom():
    """Both location_id and custom_location_name → ValidationError."""
    with pytest.raises(ValidationError):
        AdminAccidentOpenRequest(
            project_id=1,
            location_id=5,
            custom_location_name="Portaria",
        )


def test_admin_open_request_accepts_only_location_id():
    req = AdminAccidentOpenRequest(project_id=1, location_id=5)
    assert req.location_id == 5
    assert req.custom_location_name is None


def test_admin_open_request_accepts_only_custom_location():
    req = AdminAccidentOpenRequest(project_id=1, custom_location_name="Portaria Norte")
    assert req.location_id is None
    assert req.custom_location_name == "Portaria Norte"


# ---------------------------------------------------------------------------
# WebAccidentOpenRequest — chave normalisation + location xor
# ---------------------------------------------------------------------------


def test_web_open_request_normalizes_chave():
    """Lowercase chave gets uppercased."""
    req = WebAccidentOpenRequest(
        chave="ab12",
        project_id=1,
        location_id=3,
        custom_location_name=None,
        zone="safety",
        status="ok",
    )
    assert req.chave == "AB12"


def test_web_open_request_rejects_short_chave():
    with pytest.raises(ValidationError):
        WebAccidentOpenRequest(
            chave="AB1",
            project_id=1,
            location_id=3,
            custom_location_name=None,
            zone="safety",
            status="ok",
        )


def test_web_open_request_rejects_no_location():
    with pytest.raises(ValidationError):
        WebAccidentOpenRequest(
            chave="AB12",
            project_id=1,
            location_id=None,
            custom_location_name=None,
            zone="safety",
            status="ok",
        )


def test_web_open_request_rejects_both_locations():
    with pytest.raises(ValidationError):
        WebAccidentOpenRequest(
            chave="AB12",
            project_id=1,
            location_id=3,
            custom_location_name="Portaria",
            zone="safety",
            status="ok",
        )


# ---------------------------------------------------------------------------
# SituacaoPessoalRow — Literal enforcement
# ---------------------------------------------------------------------------


def test_situacao_pessoal_row_zone_status_literal_enforced():
    from datetime import datetime, timezone

    valid_base = dict(
        user_id=1,
        event_time=datetime.now(tz=timezone.utc),
        name="João",
        chave="AA00",
        projects=["Proj A"],
        local="Galpão",
        phone=None,
        videos=[],
        priority=2,
        row_color="white",
    )

    # Valid row
    row = SituacaoPessoalRow(**valid_base, zone="Aguardando", status="OK")
    assert row.zone == "Aguardando"
    assert row.status == "OK"

    # Invalid zone
    with pytest.raises(ValidationError):
        SituacaoPessoalRow(**valid_base, zone="invalido", status="OK")

    # Invalid status
    with pytest.raises(ValidationError):
        SituacaoPessoalRow(**valid_base, zone="Acidente", status="invalido")


# ---------------------------------------------------------------------------
# AccidentSummary — label format (schema accepts arbitrary string)
# ---------------------------------------------------------------------------


def test_accident_summary_label_format():
    """Schema accepts a zero-padded 4-digit string like '0042'."""
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    summary = AccidentSummary(
        id=1,
        accident_number=42,
        accident_number_label="0042",
        project_name="Obra Central",
        location_name="Portaria",
        location_is_registered=True,
        origin="admin",
        opened_by_label="Admin João",
        opened_at=now,
        closed_at=None,
    )
    assert summary.accident_number_label == "0042"

    # Any string is accepted (formatting is the service's responsibility)
    summary2 = AccidentSummary(
        id=2,
        accident_number=0,
        accident_number_label="0000",
        project_name="Obra Norte",
        location_name="Sala A",
        location_is_registered=False,
        origin="web",
        opened_by_label="User Maria",
        opened_at=now,
        closed_at=now,
    )
    assert summary2.accident_number_label == "0000"
