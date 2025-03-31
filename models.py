import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    full_name = Column(String, nullable=True)

    links = relationship("Link", back_populates="owner")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)

    redirect_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=True)

    owner = relationship("User", back_populates="links")
