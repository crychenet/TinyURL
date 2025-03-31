from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from init_redis import redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timezone
from json import dumps, loads

from models import Link, User
from routes.schemas import LinkCreate, LinkResponse, LinkStats, LinkUpdate
from db import get_async_session
from auth.users import current_active_user
from utils import generate_short_code
from config import LINK_TTL_SECONDS, STATS_TTL_SECONDS


router = APIRouter(prefix="/links", tags=["links"])


@router.post("/shorten", response_model=LinkResponse)
async def create_short_link(
    link_data: LinkCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    if link_data.custom_alias:
        existing = await session.execute(
            select(Link).where(Link.short_code == link_data.custom_alias)
        )
        if existing.scalar():
            raise HTTPException(status_code=409, detail="Alias already exists")
        short_code = link_data.custom_alias
    else:
        while True:
            code = generate_short_code()
            exists = await session.execute(
                select(Link).where(Link.short_code == code)
            )
            if not exists.scalar():
                short_code = code
                break

    new_link = Link(
        original_url=str(link_data.original_url),
        short_code=short_code,
        created_at=datetime.now(timezone.utc),
        expires_at=link_data.expires_at,
        user_id=str(user.id),
    )

    session.add(new_link)
    await session.commit()
    await session.refresh(new_link)

    await redis_client.setex(
        f"link:{short_code}",
        LINK_TTL_SECONDS,
        dumps({
            "original_url": new_link.original_url,
            "expires_at": new_link.expires_at.isoformat() if new_link.expires_at else None
        })
    )

    return new_link


@router.get("/search", response_model=list[LinkResponse])
async def search_by_original_url(
    original_url: str = Query(..., description="Original long URL"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    url_str = original_url.rstrip("/")

    result = await session.execute(
        select(Link).where(
            or_(
                Link.original_url == url_str,
                Link.original_url == url_str + "/"
            ),
            Link.user_id == str(user.id)
        )
    )
    links = result.scalars().all()

    return links


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    cache_key = f"link:{short_code}"
    cached = await redis_client.get(cache_key)

    if cached:
        link_data = loads(cached)
    else:
        result = await session.execute(
            select(Link).where(Link.short_code == short_code)
        )
        link = result.scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Short link not found")

        link_data = {
            "original_url": link.original_url,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None
        }
        await redis_client.setex(cache_key, LINK_TTL_SECONDS, dumps(link_data))

    if link_data["expires_at"]:
        expires_at = datetime.fromisoformat(link_data["expires_at"]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="Link expired")

    stats_key = f"stats:{short_code}"
    await redis_client.hincrby(stats_key, "redirect_count", 1)
    await redis_client.hset(stats_key, "last_used", datetime.now(timezone.utc).isoformat())
    await redis_client.expire(stats_key, STATS_TTL_SECONDS)

    return RedirectResponse(link_data["original_url"], status_code=307)


@router.delete("/{short_code}", status_code=204)
async def delete_link(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code)
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Not your link")

    await session.delete(link)
    await session.commit()

    await redis_client.delete(f"link:{short_code}")
    await redis_client.delete(f"stats:{short_code}")


@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    link_data: LinkUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code)
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Not your link")

    link.original_url = str(link_data.original_url)
    await session.commit()
    await session.refresh(link)

    await redis_client.setex(
        f"link:{short_code}",
        LINK_TTL_SECONDS,
        dumps({
            "original_url": link.original_url,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None
        })
    )

    return link


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Link).where(Link.short_code == short_code)
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != str(user.id):
        raise HTTPException(status_code=403, detail="Not your link")

    stats_key = f"stats:{short_code}"
    stats = await redis_client.hgetall(stats_key)

    if stats:
        if "redirect_count" in stats:
            link.redirect_count = int(stats["redirect_count"])
        if "last_used" in stats:
            link.last_used = datetime.fromisoformat(stats["last_used"])

    return link
