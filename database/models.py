import datetime
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    tag: Mapped[str | None] = mapped_column(String, nullable=True)
    town_hall: Mapped[int] = mapped_column(Integer, default=0)
    total_builders: Mapped[int] = mapped_column(Integer, default=5)
    buildings_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_json_sync: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    upgrades = relationship("ActiveUpgrade", back_populates="user", cascade="all, delete-orphan")


class ActiveUpgrade(Base):
    __tablename__ = "active_upgrades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    building_name: Mapped[str] = mapped_column(String)
    building_level: Mapped[int] = mapped_column(Integer, default=1)
    target_level: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    builder_index: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="upgrades")
