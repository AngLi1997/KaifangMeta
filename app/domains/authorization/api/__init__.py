from fastapi import APIRouter

from .apis import router as apis
from .menus import router as menus
from .roles import router as roles

apis_router = APIRouter()
apis_router.include_router(apis, tags=["API模块"])

menus_router = APIRouter()
menus_router.include_router(menus, tags=["菜单模块"])

roles_router = APIRouter()
roles_router.include_router(roles, tags=["角色模块"])
