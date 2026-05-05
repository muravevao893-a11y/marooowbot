from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class GiveawayType(StrEnum):
    AUTO = 'auto'
    MANUAL = 'manual'


class GiveawayStatus(StrEnum):
    ACTIVE = 'active'
    FINISHED = 'finished'
    CANCELLED = 'cancelled'


class EntrySource(StrEnum):
    COMMENT = 'comment'
    BUTTON = 'button'


class DeliveryStatus(StrEnum):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    MANUAL_REQUIRED = 'manual_required'


class ReferralStatus(StrEnum):
    PENDING = 'pending'
    ACTIVE = 'active'
    REJECTED = 'rejected'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    entries_count: Mapped[int] = mapped_column(Integer, default=0)
    wins_count: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    entries: Mapped[list['GiveawayEntry']] = relationship(back_populates='user')
    wins: Mapped[list['GiveawayWinner']] = relationship(back_populates='user')


class Giveaway(Base):
    __tablename__ = 'giveaways'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default=GiveawayStatus.ACTIVE.value, index=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prize_name: Mapped[str] = mapped_column(String(255), default='мишка')
    gift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    winners_count: Mapped[int] = mapped_column(Integer, default=1)
    min_participants: Mapped[int] = mapped_column(Integer, default=0)

    channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    channel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    discussion_root_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    discussion_message_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    announcement_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list['GiveawayEntry']] = relationship(back_populates='giveaway')
    winners: Mapped[list['GiveawayWinner']] = relationship(back_populates='giveaway')


class GiveawayEntry(Base):
    __tablename__ = 'giveaway_entries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey('giveaways.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    comment_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default=EntrySource.BUTTON.value)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    giveaway: Mapped[Giveaway] = relationship(back_populates='entries')
    user: Mapped[User] = relationship(back_populates='entries')

    __table_args__ = (UniqueConstraint('giveaway_id', 'user_id', name='uq_giveaway_entry_user'),)


class GiveawayWinner(Base):
    __tablename__ = 'giveaway_winners'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey('giveaways.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    gift_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), default=DeliveryStatus.PENDING.value)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    giveaway: Mapped[Giveaway] = relationship(back_populates='winners')
    user: Mapped[User] = relationship(back_populates='wins')

    __table_args__ = (UniqueConstraint('giveaway_id', 'user_id', name='uq_giveaway_winner_user'),)


class ChanceAttempt(Base):
    __tablename__ = 'chance_attempts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey('giveaways.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    comment_message_id: Mapped[int] = mapped_column(Integer, unique=True)
    discussion_root_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chance_percent: Mapped[float] = mapped_column(Float)
    won: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Referral(Base):
    __tablename__ = 'referrals'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=ReferralStatus.PENDING.value, index=True)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_posts_count: Mapped[int] = mapped_column(Integer, default=0)
    bonus_percent: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint('referrer_user_id', 'referred_user_id', name='uq_referral_pair'),)


class ReferralActivity(Base):
    __tablename__ = 'referral_activity'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referral_id: Mapped[int] = mapped_column(ForeignKey('referrals.id'), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    discussion_root_message_id: Mapped[int] = mapped_column(Integer, index=True)
    comment_message_id: Mapped[int] = mapped_column(Integer, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
