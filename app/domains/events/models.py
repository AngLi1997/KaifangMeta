from tortoise import fields, models


class EventInbox(models.Model):
    """已处理的平台事件 ce-id，用于去重（至少一次投递）。"""

    ce_id = fields.CharField(max_length=64, pk=True)
    type = fields.CharField(max_length=64)
    received_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "event_inbox"
