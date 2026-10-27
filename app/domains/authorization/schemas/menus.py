from typing import Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

from app.domains.authorization.enums import MenuType


class MenuHref(BaseModel):
    href: Optional[str] = Field(default=None, max_length=500)

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        parsed = urlsplit(value)
        if value != value.strip() or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("外链必须是无账号信息的 HTTP 或 HTTPS URL")
        return value


class BaseMenu(MenuHref):
    id: int
    name: str
    path: str
    remark: Optional[dict]
    menu_type: Optional[MenuType]
    icon: Optional[str]
    order: int
    parent_id: int
    is_hidden: bool
    component: str
    keepalive: bool
    redirect: Optional[str]
    children: Optional[list["BaseMenu"]]


class MenuCreate(MenuHref):
    menu_type: MenuType = Field(default=MenuType.CATALOG.value)
    name: str = Field(example="身份账号")
    icon: Optional[str] = "ph:user-list-bold"
    path: str = Field(example="/system/account")
    order: Optional[int] = Field(example=1)
    parent_id: Optional[int] = Field(example=0, default=0)
    is_hidden: Optional[bool] = False
    component: str = Field(default="Layout", example="/system/account")
    keepalive: Optional[bool] = True
    redirect: Optional[str] = ""


class MenuUpdate(MenuHref):
    id: int
    menu_type: Optional[MenuType] = Field(example=MenuType.CATALOG.value)
    name: Optional[str] = Field(example="身份账号")
    icon: Optional[str] = "ph:user-list-bold"
    path: Optional[str] = Field(example="/system/account")
    order: Optional[int] = Field(example=1)
    parent_id: Optional[int] = Field(example=0)
    is_hidden: Optional[bool] = False
    component: str = Field(example="/system/account")
    keepalive: Optional[bool] = False
    redirect: Optional[str] = ""
