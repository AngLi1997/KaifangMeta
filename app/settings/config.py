import os
import typing

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BASE_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))


class Settings(BaseSettings):
    # 单一配置入口：仓库根目录 .env（模板见 .env.example）
    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, ".env"), extra="ignore")

    VERSION: str = "0.1.0"
    APP_TITLE: str = "KaifangMeta"
    PROJECT_NAME: str = "KaifangMetaPlatform"
    APP_DESCRIPTION: str = "kaifang-meta 中台平台"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True

    PROJECT_ROOT: str = PROJECT_ROOT
    BASE_DIR: str = BASE_DIR
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")

    # ---- 认证模块（docs/platform/auth/identity.md、docs/gateway.md「Token 设计」）----
    IAM_ISSUER: str = "http://localhost:9080/kaifang-meta/iam"
    IAM_SCHEMA: str = "iam"
    # 系统租户：唯一的初始化租户（默认租户），平台超级管理员所在，持有 system 范围，可跨租户管理（docs/gateway.md「轻租户」）
    IAM_SYSTEM_TENANT: str = "t_system"
    IAM_ACCESS_TOKEN_TTL: int = 15 * 60
    IAM_REFRESH_TOKEN_TTL: int = 8 * 60 * 60
    IAM_SSO_SESSION_TTL: int = 8 * 60 * 60
    IAM_COOKIE_SECURE: bool = False
    IAM_SERVICE_TOKEN_TTL: int = 10 * 60
    IAM_KEY_CACHE_TTL: int = 5 * 60
    # 平台自身作为 Service Token / 代表用户 Token 的 aud，平台 API 路由的网关签名密钥
    PLATFORM_CLIENT_ID: str = "kaifang-meta-platform"
    PLATFORM_GATEWAY_SECRET: str = "change-me-openssl-rand-hex-32"

    # ---- 平台控制台：内置应用 kaifang-meta-console（模式 A 网关托管）----
    CONSOLE_CLIENT_ID: str = "kaifang-meta-console"
    CONSOLE_REDIRECT_URIS: str = "http://localhost:3001/auth/callback"
    CONSOLE_POST_LOGOUT_REDIRECT_URIS: str = "http://localhost:3001/"
    CONSOLE_GATEWAY_PREFIX: str = "/kaifang-meta/console"
    CONSOLE_GATEWAY_SECRET: str = "change-me-openssl-rand-hex-32"
    # 控制台接收平台事件（user.disabled 等）：不经网关直连，HMAC 验签
    CONSOLE_EVENT_ENDPOINT: str = "http://127.0.0.1:8080/kaifang-meta/console/api/v1/events"
    CONSOLE_EVENT_SECRET: str = "change-me-openssl-rand-hex-32"
    # 网关限流：应用 × 租户每秒请求数；登录接口按来源 IP 每分钟次数
    CONSOLE_RATE_LIMIT_QPS: int = 200
    IAM_LOGIN_RATE_LIMIT_PER_MIN: int = 20

    # ---- 网关下发：只有认证模块持 Admin Key ----
    APISIX_ADMIN_URL: str = "http://127.0.0.1:9180"
    APISIX_ADMIN_KEY: str = ""
    # APISIX 容器访问平台进程的全部节点（主机 IP:端口，逗号分隔）；每个节点下发同一份列表
    PLATFORM_UPSTREAM_NODES: str = "host.docker.internal:8080"

    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "kaifang-meta-platform"
    POSTGRES_SCHEMA: str = "console_authz"
    # 平台进程运行时账号：非超级用户、不绕过 RLS，由 alembic 创建授权；POSTGRES_USER 只用于迁移
    POSTGRES_APP_USER: str = "kaifang_meta_app"
    POSTGRES_APP_PASSWORD: str = "change-me-app-password"
    # 每个进程每个模块连接一个池；控制台请求整程各占 default / iam 一个连接，默认 5 会挤占登录
    POSTGRES_POOL_MAX: int = 10

    # 首个超级管理员：认证模块建身份账号，控制台按 sub 建本地用户（alembic seed）
    CONSOLE_ADMIN_USERNAME: str = "admin"
    CONSOLE_ADMIN_PASSWORD: str = "123456"
    CONSOLE_ADMIN_EMAIL: str = "admin@admin.com"

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET: str = "kaifang-meta-platform"
    MINIO_SECURE: bool = False

    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    @property
    def DATABASE_URL(self) -> str:
        """alembic 使用的同步连接串"""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def API_PREFIX(self) -> str:
        return f"{self.CONSOLE_GATEWAY_PREFIX}/api"

    def _pg(self, schema: str) -> dict:
        return {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": self.POSTGRES_HOST,
                "port": self.POSTGRES_PORT,
                "user": self.POSTGRES_APP_USER,
                "password": self.POSTGRES_APP_PASSWORD,
                "database": self.POSTGRES_DB,
                # 表结构由 alembic 管理；每个模块一个连接，只在本模块 schema 内读写
                "server_settings": {"search_path": schema},
                "maxsize": self.POSTGRES_POOL_MAX,
            },
        }

    @property
    def TORTOISE_ORM(self) -> dict:
        return {
            "connections": {
                "default": self._pg(self.POSTGRES_SCHEMA),
                "iam": self._pg(self.IAM_SCHEMA),
            },
            "apps": {
                "models": {
                    "models": [
                        "app.domains.users.models",
                        "app.domains.authorization.models",
                        "app.domains.auditlog.models",
                        "app.domains.events.models",
                    ],
                    "default_connection": "default",
                },
                "iam": {
                    "models": ["app.iam.models"],
                    "default_connection": "iam",
                },
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }


settings = Settings()
