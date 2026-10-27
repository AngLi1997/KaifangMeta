FROM node:20-alpine AS web

WORKDIR /opt/kaifang-meta-platform
# 前端读取根目录 .env；构建只需要非敏感的 VITE_* / CONSOLE_CLIENT_ID，取自模板
COPY .env.example ./.env
COPY web ./web
RUN cd web && corepack enable && pnpm i && pnpm build


FROM python:3.11-slim-bullseye

WORKDIR /opt/kaifang-meta-platform
ADD . .
COPY docker/entrypoint.sh .

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core-apt \
    --mount=type=cache,target=/var/lib/apt,sharing=locked,id=core-apt \
    sed -i "s@http://.*.debian.org@http://mirrors.ustc.edu.cn@g" /etc/apt/sources.list \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev bash nginx vim curl procps net-tools

RUN pip install -r docker/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY --from=web /opt/kaifang-meta-platform/web/dist /opt/kaifang-meta-platform/web/dist
COPY docker/web.conf /etc/nginx/sites-available/web.conf
RUN rm -f /etc/nginx/sites-enabled/default \ 
    && ln -s /etc/nginx/sites-available/web.conf /etc/nginx/sites-enabled/ 

ENV LANG=zh_CN.UTF-8
EXPOSE 80 8080

ENTRYPOINT [ "sh", "entrypoint.sh" ]
