"""接收平台事件（不经网关）：校验 X-KM-Event-Sign → ce-id 去重 → 处理（docs/communication.md「事件投递」）"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from tortoise.transactions import in_transaction

from app.log import logger
from app.domains.events.models import EventInbox
from app.domains.users.models import User
from app.iam import service as iam
from app.schemas.base import Success
from app.settings import settings

router = APIRouter()

SIGN_WINDOW_SECONDS = 5 * 60


@router.post("", summary="接收平台事件")
async def receive_event(request: Request):
    body = await request.body()
    ce_id, ce_time = request.headers.get("ce-id", ""), request.headers.get("ce-time", "")
    sign = request.headers.get("x-km-event-sign", "")
    expected = hmac.new(
        settings.CONSOLE_EVENT_SECRET.encode(), ce_id.encode() + ce_time.encode() + body, hashlib.sha256
    ).hexdigest()
    if not (ce_id and sign and hmac.compare_digest(expected, sign)):
        raise HTTPException(status_code=401, detail="事件签名无效")
    try:
        sent_at = datetime.fromisoformat(ce_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="ce-time 格式错误")
    if abs((datetime.now(timezone.utc) - sent_at).total_seconds()) > SIGN_WINDOW_SECONDS:
        raise HTTPException(status_code=401, detail="事件已过期")

    event = json.loads(body)
    async with in_transaction("default") as conn:
        if await EventInbox.filter(ce_id=ce_id).using_db(conn).exists():
            return Success(msg="duplicate")
        await EventInbox.create(using_db=conn, ce_id=ce_id, type=event["type"])
        sub = (event.get("data") or {}).get("sub")
        if event["type"] in ("user.disabled", "user.enabled", "user.updated") and sub:
            # 事件只当变更通知：重试可能让旧事件晚到，按认证模块的当前状态同步本地映射
            account = await iam.get_account(sub)
            if account:
                await User.filter(sub=sub).using_db(conn).update(
                    is_active=account["status"] == "active", username=account["username"]
                )
                logger.info(f"{event['type']}：已同步控制台用户 sub={sub} status={account['status']}")
    return Success()
