import string
import random
from datetime import datetime, timedelta, timezone


def generate_short_code(length: int = 6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)
