"""kaifang-meta-platform-worker：与平台同一代码库的独立进程，当前负责事件分发（outbox → delivery → HTTP POST）

启动：python -m app.worker；可多实例运行，领取记录使用 FOR UPDATE SKIP LOCKED。
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from fnmatch import fnmatch

import httpx
from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.iam.models import Client
from app.log import logger
from app.settings import settings

# 失败重试间隔（秒）：1m / 5m / 30m / 2h / 12h，超过后标记 dead（docs/communication.md「事件投递」）
BACKOFF = [60, 300, 1800, 7200, 43200]
# 领取投递后的租约，进程崩溃时到期由其他实例接手
LEASE_SECONDS = 60
DELIVERY_TIMEOUT = 10
# shortcut: 轮询间隔 1 秒；事件量大时改为 LISTEN/NOTIFY 唤醒
POLL_SECONDS = 1
# 已送达的投递与无未完成投递的事件保留天数；死信保留供排查
RETENTION_DAYS = 30
PURGE_EVERY_SECONDS = 3600


def _subscribed(client: Client, event_type: str, tenant_id: str) -> bool:
    return (
        bool(client.event_endpoint)
        and tenant_id in client.tenants
        and any(fnmatch(event_type, pattern) for pattern in client.event_subscribe)
    )


async def expand_outbox() -> int:
    """把未分发的 outbox 按订阅展开为每个应用一条 delivery"""
    async with in_transaction("iam") as conn:
        rows = await conn.execute_query_dict(
            "SELECT id, type, tenant_id FROM outbox WHERE NOT dispatched ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED"
        )
        if not rows:
            return 0
        clients = await Client.filter(status="online").using_db(conn)
        for row in rows:
            for client in clients:
                if _subscribed(client, row["type"], row["tenant_id"]):
                    await conn.execute_query(
                        "INSERT INTO delivery (outbox_id, client_id, next_attempt_at) VALUES ($1, $2, now()) "
                        "ON CONFLICT (outbox_id, client_id) DO NOTHING",
                        [row["id"], client.client_id],
                    )
        await conn.execute_query("UPDATE outbox SET dispatched = true WHERE id = ANY($1)", [[r["id"] for r in rows]])
    return len(rows)


async def claim_deliveries() -> list[dict]:
    """领取到期的投递并加租约，同时带出事件内容"""
    async with in_transaction("iam") as conn:
        return await conn.execute_query_dict(
            f"""UPDATE delivery d SET next_attempt_at = now() + interval '{LEASE_SECONDS} seconds'
                FROM outbox o
                WHERE o.id = d.outbox_id AND d.id IN (
                    SELECT id FROM delivery WHERE status = 'pending' AND next_attempt_at <= now()
                    ORDER BY id LIMIT 50 FOR UPDATE SKIP LOCKED
                )
                RETURNING d.id, d.outbox_id, d.client_id, d.attempts,
                          o.type, o.subject, o.tenant_id, o.data, o.created_at"""
        )


def build_request(row: dict, secret: str) -> tuple[bytes, dict]:
    ce_id = f"evt_{row['outbox_id']}"
    body = json.dumps(
        {
            "specversion": "1.0",
            "id": ce_id,
            "source": "/kaifang-meta/iam",
            "type": row["type"],
            "subject": row["subject"],
            "time": row["created_at"].isoformat(),
            "tenantid": row["tenant_id"],
            "data": json.loads(row["data"]) if isinstance(row["data"], str) else row["data"],
        },
        ensure_ascii=False,
    ).encode()
    # ce-time 为发送时间，接收方按 ±5 分钟时间窗校验；事件发生时间在 body.time
    ce_time = datetime.now(timezone.utc).isoformat()
    sign = hmac.new(secret.encode(), ce_id.encode() + ce_time.encode() + body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/cloudevents+json",
        "ce-id": ce_id,
        "ce-time": ce_time,
        "ce-type": row["type"],
        "X-KM-Event-Sign": sign,
    }
    return body, headers


async def deliver(http: httpx.AsyncClient, row: dict) -> None:
    client = await Client.get_or_none(client_id=row["client_id"])
    error = None
    if not client or not client.event_endpoint or not client.event_secret:
        error = "应用不存在或未配置事件地址"
    else:
        body, headers = build_request(row, client.event_secret)
        try:
            resp = await http.post(client.event_endpoint, content=body, headers=headers)
            if resp.is_success:
                await Tortoise.get_connection("iam").execute_query(
                    "UPDATE delivery SET status = 'delivered', delivered_at = now(), attempts = attempts + 1, "
                    "last_error = NULL WHERE id = $1",
                    [row["id"]],
                )
                logger.info(f"事件已送达 {row['type']} → {row['client_id']}")
                return
            error = f"HTTP {resp.status_code}"
        except httpx.HTTPError as e:
            error = repr(e)

    attempts = row["attempts"] + 1
    if attempts > len(BACKOFF):
        await Tortoise.get_connection("iam").execute_query(
            "UPDATE delivery SET status = 'dead', attempts = $2, last_error = $3 WHERE id = $1",
            [row["id"], attempts, error[:500]],
        )
        logger.error(f"事件投递进入死信 {row['type']} → {row['client_id']}：{error}")
        return
    await Tortoise.get_connection("iam").execute_query(
        "UPDATE delivery SET attempts = $2, last_error = $3, "
        "next_attempt_at = now() + make_interval(secs => $4) WHERE id = $1",
        [row["id"], attempts, error[:500], BACKOFF[attempts - 1]],
    )
    logger.warning(f"事件投递失败 {row['type']} → {row['client_id']}（第 {attempts} 次）：{error}")


async def purge_delivered() -> None:
    """清理过期的已送达投递，再清理不再被任何投递引用的已分发事件；多实例重复执行无副作用"""
    async with in_transaction("iam") as conn:
        await conn.execute_query(
            "DELETE FROM delivery WHERE status = 'delivered' AND delivered_at < now() - make_interval(days => $1)",
            [RETENTION_DAYS],
        )
        await conn.execute_query(
            "DELETE FROM outbox o WHERE dispatched AND created_at < now() - make_interval(days => $1) "
            "AND NOT EXISTS (SELECT 1 FROM delivery d WHERE d.outbox_id = o.id)",
            [RETENTION_DAYS],
        )


async def run_once(http: httpx.AsyncClient) -> int:
    await expand_outbox()
    rows = await claim_deliveries()
    await asyncio.gather(*(deliver(http, row) for row in rows))
    return len(rows)


async def main() -> None:
    await Tortoise.init(config=settings.TORTOISE_ORM)
    logger.info("kaifang-meta-platform-worker 已启动：事件分发")
    try:
        async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT) as http:
            purged_at = float("-inf")
            while True:
                try:
                    await run_once(http)
                    if time.monotonic() - purged_at > PURGE_EVERY_SECONDS:
                        await purge_delivered()
                        purged_at = time.monotonic()
                except Exception as e:  # 单轮失败不退出进程，下一轮重试
                    logger.exception(f"事件分发异常：{e!r}")
                await asyncio.sleep(POLL_SECONDS)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
