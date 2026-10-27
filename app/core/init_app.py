import httpx
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from app.api import api_router
from app.domains.authorization.controllers.api import api_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.iam.api import router as iam_router
from app.iam.gateway import sync_platform_routes
from app.iam.platform_api import router as iam_platform_router
from app.log import logger
from app.settings.config import settings

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/kaifang-meta/iam/",
                "/kaifang-meta/platform/",
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)


def register_routers(app: FastAPI):
    # 控制台 API 与网关前缀同路径（模式 A 签名覆盖原始路径），认证模块挂在 /kaifang-meta/iam
    app.include_router(api_router, prefix=settings.API_PREFIX)
    app.include_router(iam_router)
    app.include_router(iam_platform_router)


async def init_db():
    # 表结构与 seed 数据由 alembic 管理（alembic upgrade head），这里只建立连接
    await Tortoise.init(config=settings.TORTOISE_ORM)
    # 接口清单随代码变化，启动时同步到 API 表（新接口默认只有超管可用，需在角色中授权）
    await api_controller.refresh_api()
    try:
        await sync_platform_routes()
    except httpx.HTTPError as e:
        logger.warning(f"网关路由下发失败：{e!r}")
