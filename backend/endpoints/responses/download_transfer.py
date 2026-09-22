from pydantic import ConfigDict, Field

from .base import BaseModel, UTCDatetime


class DownloadTransferCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    mode: str = Field(pattern=r"^(standard|enhanced)$")
    member_ids: list[str] | None = Field(default=None, min_length=1, max_length=4096)


class DownloadTransferObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(
        pattern=r"^(handoff|progress|pause|resume|verified|cancel|fail)$"
    )
    observed_bytes: int = Field(default=0, ge=0, le=2**63 - 1)
    error_code: str | None = Field(default=None, max_length=64, pattern=r"^[ -~]*$")
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DownloadTransferItemResponse(BaseModel):
    id: int
    manifest_member_id: str
    destination: str
    expected_bytes: int
    observed_bytes: int
    status: str
    started_at: UTCDatetime | None
    last_activity_at: UTCDatetime | None
    ended_at: UTCDatetime | None


class DownloadTransferEventResponse(BaseModel):
    ordinal: int
    event_type: str
    observed_bytes: int
    error_code: str | None
    occurred_at: UTCDatetime


class DownloadTransferResponse(BaseModel):
    schema_version: int = 1
    id: str
    manifest_id: str
    rom_id: int
    mode: str
    status: str
    result: str | None = None
    selected_items: int
    selected_bytes: int
    observed_bytes: int
    started_at: UTCDatetime
    last_activity_at: UTCDatetime
    ended_at: UTCDatetime | None
    items: list[DownloadTransferItemResponse]
    events: list[DownloadTransferEventResponse]
