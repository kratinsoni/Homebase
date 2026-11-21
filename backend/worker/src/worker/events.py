import json

from redis.asyncio import Redis
from worker.config.settings import settings

STREAM_TTL_S = 3600

def conversation_stream_key(conversation_id: str) -> str:
    return f"events:conv:{conversation_id}"

class EventPublisher:
    def __init__(self, conversation_id: str, redis: Redis, task_id: str):
        self.key = conversation_stream_key(conversation_id)
        self.redis = redis
        self.task_id = task_id

    async def emit(self, type_: str, **data):
        data["task_id"] = self.task_id
        await self.redis.xadd(
            name=self.key,
            fields={"type": type_, "data": json.dumps(data)},
            maxlen=10_1000,
            approximate=True
        )

        await self.redis.expire(self.key, STREAM_TTL_S)
