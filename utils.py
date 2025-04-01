import csv
import string
import random
from io import StringIO
from datetime import datetime, timezone, timedelta
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Link, User
from db import get_async_session
from cache.link_cache import get_link_stats, set_link_in_cache
from config import STATS_SYNC_INTERVAL_SECONDS


async def sync_stats_once():
    session_gen = get_async_session()
    session = await anext(session_gen)
    try:
        result = await session.execute(select(Link))
        links = result.scalars().all()

        for link in links:
            stats = await get_link_stats(link.short_code)
            if not stats:
                continue

            updated = False

            if "redirect_count" in stats:
                try:
                    redis_count = int(stats["redirect_count"])
                    if link.redirect_count != redis_count:
                        link.redirect_count = redis_count
                        updated = True
                except Exception as e:
                    pass

            if "last_used" in stats:
                try:
                    redis_last_used = datetime.fromisoformat(stats["last_used"])
                    if not link.last_used or redis_last_used > link.last_used:
                        link.last_used = redis_last_used
                        updated = True
                except Exception as e:
                    pass

            if updated:
                session.add(link)

        await session.commit()

    finally:
        await session.close()


async def start_stats_sync_loop():
    while True:
        try:
            await sync_stats_once()
        except Exception as e:
            pass
        await asyncio.sleep(STATS_SYNC_INTERVAL_SECONDS)


def _generate_short_code(length: int = 6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)


async def process_csv_import(content: bytes, session: AsyncSession, user: User):
    decoded = content.decode("utf-8")
    reader = csv.DictReader(StringIO(decoded))

    created_links = []
    errors = []

    for idx, row in enumerate(reader, start=1):
        original_url = row.get("original_url", "").strip()
        custom_alias = row.get("custom_alias", "").strip() or None

        if not original_url:
            errors.append({"row": idx, "error": "Missing original_url"})
            continue

        if custom_alias:
            result = await session.execute(
                select(Link).where(Link.short_code == custom_alias)
            )
            if result.scalar():
                errors.append({"row": idx, "error": f"Alias '{custom_alias}' already exists"})
                continue
            short_code = custom_alias
        else:
            while True:
                code = _generate_short_code()
                result = await session.execute(
                    select(Link).where(Link.short_code == code)
                )
                if not result.scalar():
                    short_code = code
                    break

        link = Link(
            original_url=original_url,
            short_code=short_code,
            created_at=datetime.now(timezone.utc),
            user_id=str(user.id),
        )

        session.add(link)
        await session.flush()
        await set_link_in_cache(link)
        created_links.append({
            "original_url": original_url,
            "short_code": short_code
        })

    await session.commit()

    return {"created": created_links, "errors": errors}

