from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class AccountCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    member_tenant_ids: list[str] = []

    @field_validator("tenant_id", "username", mode="before")
    @classmethod
    def strip_identity_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", "name", "phone", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class AccountUpdate(BaseModel):
    sub: str = Field(min_length=1, max_length=32)
    tenant_id: str = Field(min_length=1, max_length=32)
    username: str = Field(min_length=1, max_length=64)
    email: EmailStr | None
    name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    status: Literal["active", "disabled"]
    password: str | None = Field(default=None, min_length=8, max_length=128)
    # 不传则不改成员租户
    member_tenant_ids: list[str] | None = None

    @field_validator("sub", "tenant_id", "username", mode="before")
    @classmethod
    def strip_identity_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", "name", "phone", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value
