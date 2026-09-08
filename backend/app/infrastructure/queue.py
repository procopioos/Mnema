from collections.abc import AsyncIterator
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends

from app.core.config import get_settings


async def get_arq_redis() -> AsyncIterator[ArqRedis]:
    redis = ArqRedis.from_url(get_settings().redis_url)
    try:
        yield redis
    finally:
        await redis.aclose()


ArqRedisDep = Annotated[ArqRedis, Depends(get_arq_redis)]
