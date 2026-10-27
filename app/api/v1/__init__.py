from fastapi import APIRouter

from app.core.dependency import DependPermission

from app.domains.accounts.api import router as accounts_router
from app.domains.annotation.api import router as annotation_router
from app.domains.auditlog.api import router as auditlog_router
from app.domains.authorization.api import apis_router, menus_router, roles_router
from app.domains.events.api import router as events_router
from app.domains.tenants.api import router as tenants_router
from app.domains.users.api import router as users_router
from app.domains.users.profile import router as base_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base", tags=["基础模块"])
v1_router.include_router(users_router, prefix="/user", tags=["身份账号关联信息"], dependencies=[DependPermission])
v1_router.include_router(roles_router, prefix="/role", dependencies=[DependPermission])
v1_router.include_router(menus_router, prefix="/menu", dependencies=[DependPermission])
v1_router.include_router(apis_router, prefix="/api", dependencies=[DependPermission])
v1_router.include_router(auditlog_router, prefix="/auditlog", tags=["审计日志模块"], dependencies=[DependPermission])
v1_router.include_router(accounts_router, prefix="/account", tags=["身份账号"], dependencies=[DependPermission])
v1_router.include_router(tenants_router, prefix="/tenant", tags=["租户"], dependencies=[DependPermission])
v1_router.include_router(annotation_router, prefix="/annotation", tags=["数据标注"], dependencies=[DependPermission])
# 平台事件回调：不经网关，自行校验事件签名
v1_router.include_router(events_router, prefix="/events", tags=["平台事件"])
