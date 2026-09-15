from pydantic import ConfigDict, Field, field_validator

from .base import BaseModel, UTCDatetime


class DownloadManifestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("component_ids")
    @classmethod
    def validate_component_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and (
            any(component_id <= 0 for component_id in value)
            or len(value) != len(set(value))
        ):
            raise ValueError("component ids must be unique positive integers")
        return value


class DownloadManifestComponentSchema(BaseModel):
    component_id: int
    kind: str


class DownloadManifestMemberSchema(BaseModel):
    file_id: int
    destination: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot: str = Field(pattern=r'^".+"$')
    download: str = Field(
        pattern=r"^/api/download-manifests/[0-9a-f-]{36}/files/[0-9]+$"
    )


class DownloadManifestResponse(BaseModel):
    schema_version: int = 1
    id: str
    created_at: UTCDatetime
    expires_at: UTCDatetime
    components: list[DownloadManifestComponentSchema]
    members: list[DownloadManifestMemberSchema]
