from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


class GiveawayType:
    AUTO = "auto"
    MANUAL = "manual"


class GiveawayStatus:
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class EntrySource:
    COMMENT = "comment"
    BUTTON = "button"


class DeliveryStatus:
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"


class ReferralStatus:
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    entries_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    wins_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default=GiveawayStatus.ACTIVE, server_default=text("'active'"))

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prize_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    winners_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    min_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    require_subscription: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    chance_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    referral_bonus_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discussion_root_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_message_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    announcement_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)


class GiveawayEntry(Base):
    __tablename__ = "giveaway_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default=EntrySource.BUTTON, server_default=text("'button'"))
    comment_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("giveaway_id", "user_id", name="uq_giveaway_entry_user"),
    )


class ChanceAttempt(Base):
    __tablename__ = "chance_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    discussion_root_message_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    comment_message_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    skipped_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chance_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)


class GiveawayWinner(Base):
    __tablename__ = "giveaway_winners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    prize_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default=DeliveryStatus.PENDING, server_default=text("'pending'"))
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReferralStatus.PENDING, server_default=text("'pending'"))
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    unique_posts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    bonus_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("referrer_user_id", "referred_user_id", name="uq_referral_pair"),
    )


class ReferralActivity(Base):
    __tablename__ = "referral_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referral_id: Mapped[int] = mapped_column(ForeignKey("referrals.id", ondelete="CASCADE"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    discussion_root_message_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    comment_message_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now_dt, server_default=func.now(), nullable=False)
