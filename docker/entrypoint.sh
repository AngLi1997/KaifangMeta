#!/bin/sh
set -e

# 网关地址（APISIX 数据面 / SLB），默认同主机 9080
sed -i "s#GATEWAY_UPSTREAM#${GATEWAY_UPSTREAM:-127.0.0.1:9080}#" /etc/nginx/sites-available/web.conf
# 对象存储同源反代：与平台进程使用同一个 MINIO_ENDPOINT
[ "${MINIO_SECURE:-false}" = true ] && MINIO_SCHEME=https || MINIO_SCHEME=http
sed -i "s#MINIO_BUCKET#${MINIO_BUCKET:-kaifang-meta-platform}#; s#MINIO_SCHEME#${MINIO_SCHEME}#; s#MINIO_ENDPOINT#${MINIO_ENDPOINT:-127.0.0.1:9000}#g" /etc/nginx/sites-available/web.conf

alembic upgrade head
nginx
# 同一镜像：ROLE=worker 时作为 kaifang-meta-platform-worker 运行
if [ "$ROLE" = "worker" ]; then
  exec python -m app.worker
fi
exec python run.py
