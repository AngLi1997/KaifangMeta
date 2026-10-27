#!/bin/sh
# KaifangMetaPlatform 本地启动：基础设施（Docker）+ 数据库迁移 + 前后端源码启动
# 用法：sh start-service.sh        sh stop-service.sh 停止前后端（基础设施容器保持运行）
set -e

ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT"

log() { printf '\033[36m[kaifang-meta]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[kaifang-meta]\033[0m %s\n' "$*" >&2; exit 1; }

# ---- 配置：根目录 .env 是唯一入口 ----
if [ ! -f .env ]; then
  cp .env.example .env
  # 本地生成签名密钥，避免使用模板占位值
  for key in CONSOLE_GATEWAY_SECRET CONSOLE_EVENT_SECRET PLATFORM_GATEWAY_SECRET POSTGRES_APP_PASSWORD; do
    sed -i.bak "s/^$key=.*/$key=$(openssl rand -hex 32)/" .env
  done
  rm -f .env.bak
  log "已由 .env.example 生成 .env"
fi
set -a
. ./.env
set +a

command -v docker >/dev/null || die "未找到 docker"
docker info >/dev/null 2>&1 || die "Docker 未运行"
command -v uv >/dev/null || die "未找到 uv（https://docs.astral.sh/uv/）"
command -v pnpm >/dev/null || die "未找到 pnpm（npm i -g pnpm）"

# 停止上次由本脚本启动的后端、worker 与前端
sh "$ROOT/stop-service.sh"

# ---- 端口冲突：停止占用者，优先启动本服务 ----
# 端口被其他 Docker 容器占用时停止该容器；被普通进程占用时结束该进程（Docker 自身的转发进程除外）
free_port() {
  port=$1
  for c in $(docker ps --filter "publish=$port" --format '{{.Names}}'); do
    case "$c" in
      kaifang-meta-*) ;;
      *) log "端口 $port 被容器 $c 占用，停止该容器"; docker stop "$c" >/dev/null ;;
    esac
  done
  for pid in $(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null); do
    name=$(ps -p "$pid" -o comm= 2>/dev/null || true)
    case "$name" in
      *com.docker*|*vpnkit*|*Docker*|*OrbStack*) ;;
      *) log "端口 $port 被进程 $pid（$name）占用，结束该进程"; kill "$pid" 2>/dev/null || true ;;
    esac
  done
}

for port in "$POSTGRES_PORT" "$REDIS_PORT" "$MINIO_PORT" "$MINIO_CONSOLE_PORT" "$ETCD_PORT" \
  "$APISIX_HTTP_PORT" "$APISIX_HTTPS_PORT" "$APISIX_ADMIN_PORT" "$APP_PORT" "$VITE_PORT"; do
  free_port "$port"
done
sleep 1

# ---- 基础设施 ----
log "启动基础设施（PostgreSQL / Redis / MinIO / etcd / APISIX）"
docker compose --project-directory "$ROOT" -f "$ROOT/docker/docker-compose.yml" up -d --wait

log "创建 MinIO bucket：$MINIO_BUCKET"
docker exec kaifang-meta-minio mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
docker exec kaifang-meta-minio mc mb --ignore-existing "local/$MINIO_BUCKET" >/dev/null
log "etcd 控制台 http://localhost:${ETCD_WORKBENCH_PORT:-9010}（首次登录后连接 etcd:2379）"

# km-* 插件以挂载方式加载，重载使本地改动生效（生产随网关镜像发布）
docker exec kaifang-meta-apisix apisix reload >/dev/null 2>&1 || true

# 平台路由由认证模块启动时经 Admin API 下发，这里只等待 Admin API 就绪
i=0
until curl -fs -o /dev/null "http://127.0.0.1:$APISIX_ADMIN_PORT/apisix/admin/routes" -H "X-API-KEY: $APISIX_ADMIN_KEY"; do
  i=$((i + 1)); [ $i -ge 30 ] && die "APISIX Admin API 未就绪"; sleep 1
done

# ---- 后端 ----
log "安装后端依赖"
uv sync -q
log "执行数据库迁移（alembic upgrade head）"
uv run alembic upgrade head

# ---- 前端 ----
if [ ! -d web/node_modules ]; then
  log "安装前端依赖"
  (cd web && pnpm i)
fi

# ---- 源码启动前后端 ----
PID_FILE="$ROOT/.service-pids"
: > "$PID_FILE"
cleanup() {
  trap - INT TERM EXIT
  sh "$ROOT/stop-service.sh"
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

uv run python run.py &
BACKEND_PID=$!
printf 'backend %s\n' "$BACKEND_PID" >> "$PID_FILE"
# kaifang-meta-platform-worker：事件分发（outbox → 应用事件地址）
uv run python -m app.worker &
WORKER_PID=$!
printf 'worker %s\n' "$WORKER_PID" >> "$PID_FILE"
(cd web && exec pnpm dev) &
FRONTEND_PID=$!
printf 'frontend %s\n' "$FRONTEND_PID" >> "$PID_FILE"

log "前端      http://localhost:$VITE_PORT"
log "后端      http://localhost:$APP_PORT/docs"
log "认证      http://localhost:$APISIX_HTTP_PORT/kaifang-meta/iam/.well-known/openid-configuration"
log "MinIO     http://localhost:$MINIO_CONSOLE_PORT"
log "APISIX    http://localhost:$APISIX_ADMIN_PORT/ui/"
log "etcd UI   http://localhost:${ETCD_WORKBENCH_PORT:-9010}"
wait
