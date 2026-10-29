from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OrgBase(BaseModel):
    tenant_id: str = ""
    parent_id: int | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    sort_order: int = 0

    @field_validator("code", "name", mode="before")
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class OrgCreate(OrgBase):
    pass


class OrgUpdate(OrgBase):
    id: int
    status: Literal["active", "disabled"]


class OrgImportRow(OrgBase):
    id: int = Field(gt=0)
    status: Literal["active", "disabled"] = "active"


class OrgImport(BaseModel):
    tenant_id: str = ""
    orgs: list[OrgImportRow] = Field(min_length=1, max_length=20000)
