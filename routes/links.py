from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timezone

from models import Link, User
from routes.schemas import LinkCreate, LinkResponse, LinkStats, LinkUpdate
from db import get_async_session
from auth.users import current_active_user
from utils import _generate_short_code, process_csv_import
from logger import get_logger
from cache.link_cache import (
    get_link_from_cache,
    set_link_in_cache,
    delete_link_from_cache,
    increment_link_stats,
    get_link_stats,
)


router = APIRouter(prefix="/links", tags=["links"])
logger = get_logger(__name__)


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
            code = _generate_short_code()
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

    await set_link_in_cache(new_link)
    logger.info("Short link created", extra={
        "user_id": str(user.id),
        "short_code": new_link.short_code,
        "original_url": new_link.original_url,
        "expires_at": str(new_link.expires_at)
    })
    return new_link


@router.get("/search", response_model=list[LinkResponse])
async def search_by_original_url(
    original_url: str = Query(..., description="Original long URL"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
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


@router.post("/import_csv")
async def import_links_from_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        result = await process_csv_import(content, session, user)
        logger.info(f"CSV import by user {user.id}: {len(result['created'])} created, {len(result['errors'])} errors")
        return result
    except ValueError as e:
        logger.warning(f"CSV import failed for user {user.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    link_data = await get_link_from_cache(short_code)

    if not link_data:
        result = await session.execute(
            select(Link).where(Link.short_code == short_code)
        )
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Short link not found")

        if link.expires_at and datetime.now(timezone.utc) > link.expires_at:
            raise HTTPException(status_code=410, detail="Link expired")

        link_data = {
            "original_url": link.original_url,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None
        }
        await set_link_in_cache(link)

    else:
        if link_data["expires_at"]:
            expires_at = datetime.fromisoformat(link_data["expires_at"]).replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=410, detail="Link expired")

    await increment_link_stats(short_code)
    logger.info(f"Redirected short link {short_code}")

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

    await delete_link_from_cache(short_code)
    logger.info(f"Link deleted: {short_code} by user {user.id}")


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

    await set_link_in_cache(link)
    logger.info(f"Link updated: {short_code} by user {user.id} → {link.original_url}")

    return link


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats_route(
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

    stats = await get_link_stats(short_code)

    if stats:
        if "redirect_count" in stats:
            link.redirect_count = int(stats["redirect_count"])
        if "last_used" in stats:
            link.last_used = datetime.fromisoformat(stats["last_used"])

    logger.info(f"Stats viewed for {short_code} by user {user.id}")
    return link
