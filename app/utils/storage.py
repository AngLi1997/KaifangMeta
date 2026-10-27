from minio import Minio

from app.settings import settings


def get_minio_client(*, public: bool = False) -> Minio:
    return Minio(
        settings.MINIO_PUBLIC_ENDPOINT if public else settings.MINIO_ENDPOINT,
        settings.MINIO_ROOT_USER,
        settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_PUBLIC_SECURE if public else settings.MINIO_SECURE,
        region="us-east-1" if public else None,
    )
