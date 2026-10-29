import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

NODE = re.compile(r"^[\w.-]+:\d{1,5}$")
PATH = re.compile(r"^/[\w./-]*$")


class GatewayRoute(BaseModel):
    path: str = Field(min_length=1, max_length=128)
    nodes: list[str] = Field(min_length=1)
    health: str | None = Field(default=None, max_length=255)

    @field_validator("path")
    @classmethod
    def check_path(cls, value):
        if not PATH.match(value) or value == "/":
            raise ValueError("子路径以 / 开头，如 /platform-common")
        return value.rstrip("/")

    @field_validator("nodes")
    @classmethod
    def check_nodes(cls, value):
        if not all(NODE.match(v) for v in value):
            raise ValueError("上游节点格式为 IP:端口")
        return value

    @field_validator("health", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class Gateway(BaseModel):
    prefix: str = Field(pattern=r"^/kaifang-meta/[\w-]+$")
    routes: list[GatewayRoute] = Field(min_length=1)
    public_paths: list[str] = []
    rate_limit: int = Field(default=200, ge=1, le=100000)

    @model_validator(mode="after")
    def unique_paths(self):
        paths = [r.path for r in self.routes]
        if len(set(paths)) != len(paths):
            raise ValueError("子路径重复")
        return self


class Portal(BaseModel):
    entry: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=8)
    description: str | None = Field(default=None, max_length=64)
    order: int = 100


class AppBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    owner: str | None = Field(default=None, max_length=64)
    tenants: list[str] = Field(min_length=1)
    scopes: list[str] = []
    redirect_uris: list[str] = []
    post_logout_redirect_uris: list[str] = []
    gateway: Gateway | None = None
    portal: Portal = Portal()

    def fields(self) -> dict:
        data = self.model_dump(exclude={"gateway", "portal"})
        data["gateway"] = self.gateway.model_dump() if self.gateway else {}
        data["portal"] = {k: v for k, v in self.portal.model_dump().items() if v not in (None, "")}
        return data


class AppCreate(AppBody):
    client_id: str = Field(pattern=r"^kaifang-meta-[a-z0-9-]+$", max_length=64)


class AppUpdate(AppBody):
    client_id: str


class AppStatus(BaseModel):
    client_id: str
    status: Literal["online", "disabled"]


class AppSecret(BaseModel):
    client_id: str
    kind: Literal["client", "gateway"]


class AppRef(BaseModel):
    client_id: str
