import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    modality: Literal["image", "text", "document", "video", "audio"]
    config: str = Field(min_length=1, max_length=65536)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("config")
    @classmethod
    def check_config(cls, value: str):
        try:
            root = ET.fromstring(value)
        except ET.ParseError as e:
            raise ValueError(f"模板 XML 无法解析：{e}")
        # <Workbench> 为工作台布局（docs/platform/annotation/components/），布局规则由控制台设计器校验
        if root.tag == "Workbench":
            if not len(root):
                raise ValueError("工作台为空")
        elif root.tag != "View":
            raise ValueError("模板 XML 根节点必须是 <View> 或 <Workbench>")
        return value


class TemplateCreate(TemplateBase):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9._-]*$")


class TemplateUpdate(TemplateBase):
    id: int


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    template_id: int

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ItemSave(BaseModel):
    id: int
    result: list[dict]
    draft: bool = Field(False, description="草稿：只保存结果，不改变条目状态")
