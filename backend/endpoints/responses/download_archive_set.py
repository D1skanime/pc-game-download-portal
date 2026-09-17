from pydantic import BaseModel, ConfigDict, Field, field_validator


class DownloadArchiveSetMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: int = Field(ge=1)
    manifest_member_id: int = Field(ge=1)
    required: bool = True


class DownloadArchiveSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=450)
    members: list[DownloadArchiveSetMemberRequest] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("archive set name is required")
        return value


class DownloadArchiveSetImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sets: list[DownloadArchiveSetRequest] = Field(min_length=1, max_length=100)


class DownloadArchiveSetMemberResponse(BaseModel):
    component_id: int
    manifest_member_id: int
    position: int
    required: bool


class DownloadArchiveSetResponse(BaseModel):
    id: int
    rom_id: int
    name: str
    members: list[DownloadArchiveSetMemberResponse]
