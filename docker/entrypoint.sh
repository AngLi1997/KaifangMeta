#!/bin/sh
set -e

# 网关地址（APISIX 数据面 / SLB），默认同主机 9080
sed -i "s#GATEWAY_UPSTREAM#${GATEWAY_UPSTREAM:-127.0.0.1:9080}#" /etc/nginx/sites-available/web.conf

alembic upgrade head
nginx
# 同一镜像：ROLE=worker 时作为 kaifang-meta-platform-worker 运行
if [ "$ROLE" = "worker" ]; then
  exec python -m app.worker
fi
exec python run.py
