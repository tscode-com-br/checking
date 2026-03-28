from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str
    app: str


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=2, max_length=80)
    shared_key: str


class ScanRequest(BaseModel):
    rfid: str = Field(min_length=4, max_length=64)
    local: str = Field(min_length=2, max_length=40)
    action: Literal["checkin", "checkout"]
    device_id: str = Field(min_length=2, max_length=80)
    request_id: str = Field(min_length=8, max_length=80)
    shared_key: str


class ScanResponse(BaseModel):
    outcome: Literal["submitted", "pending_registration", "invalid_key", "duplicate", "failed"]
    led: Literal["white", "orange_4s", "green_2s", "red"]
    message: str


class AdminUserUpsert(BaseModel):
    rfid: str = Field(min_length=4, max_length=64)
    nome: str = Field(min_length=3, max_length=180)
    chave: str = Field(min_length=4, max_length=4)
    projeto: Literal["P80", "P83"]

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("chave must be alphanumeric")
        return value.upper()


class UserRow(BaseModel):
    rfid: str
    nome: str
    chave: str
    projeto: str
    local: Optional[str]
    checkin: bool
    time: datetime


class PendingRow(BaseModel):
    id: int
    rfid: str
    first_seen_at: datetime
    last_seen_at: datetime
    attempts: int


class EventRow(BaseModel):
    id: int
    rfid: Optional[str]
    action: str
    status: str
    message: str
    project: Optional[str]
    event_time: datetime
