from datetime import datetime, timezone
from typing import Optional

from models import Link
from init_redis import redis_client
from config import LINK_TTL_SECONDS, STATS_TTL_SECONDS
from json import dumps, loads


def _link_key(short_code: str) -> str:
    return f"link:{short_code}"


def _stats_key(short_code: str) -> str:
    return f"stats:{short_code}"


def _serialize_link(link: Link) -> str:
    return dumps({
        "original_url": link.original_url,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None
    })


def _deserialize_link(data: str) -> dict:
    return loads(data)


def _get_ttl(expires_at: Optional[datetime]) -> int:
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        return max(ttl, 0)
    return LINK_TTL_SECONDS


async def get_link_from_cache(short_code: str) -> Optional[dict]:
    data = await redis_client.get(_link_key(short_code))
    return _deserialize_link(data) if data else None


async def set_link_in_cache(link: Link):
    ttl = _get_ttl(link.expires_at)
    await redis_client.setex(_link_key(link.short_code), ttl, _serialize_link(link))


async def delete_link_from_cache(short_code: str):
    await redis_client.delete(_link_key(short_code))
    await redis_client.delete(_stats_key(short_code))


async def increment_link_stats(short_code: str):
    stats_key = _stats_key(short_code)
    now_iso = datetime.now(timezone.utc).isoformat()

    await redis_client.hincrby(stats_key, "redirect_count", 1)
    await redis_client.hset(stats_key, "last_used", now_iso)
    await redis_client.expire(stats_key, STATS_TTL_SECONDS)


async def get_link_stats(short_code: str) -> dict:
    return await redis_client.hgetall(_stats_key(short_code))
