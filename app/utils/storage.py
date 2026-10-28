from urllib.parse import urlsplit

from minio import Minio

from app.settings import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        settings.MINIO_ROOT_USER,
        settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_SECURE,
        # 固定 region，预签名时不再请求 MinIO 查询桶位置
        region="us-east-1",
    )


def presigned_url(object_name: str) -> str:
    """浏览器下载地址：只返回路径，由访问入口（Vite / web nginx）同源反代到 MINIO_ENDPOINT，见 docs/storage.md"""
    url = get_minio_client().presigned_get_object(settings.MINIO_BUCKET, object_name)
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"
