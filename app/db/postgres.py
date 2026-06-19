from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import String, Text, DateTime, func
from app.core.config import settings

engine = create_async_engine(settings.postgres_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class FeedbackRecord(Base):
    __tablename__ = "feedback"

    id: Mapped[int]             = mapped_column(primary_key=True)
    repo: Mapped[str]           = mapped_column(String(256))
    file_path: Mapped[str]      = mapped_column(String(512))
    rule_id: Mapped[str]        = mapped_column(String(256))
    action: Mapped[str]         = mapped_column(String(64))   # suppress | confirm
    developer: Mapped[str]      = mapped_column(String(128), nullable=True)
    note: Mapped[str]           = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]= mapped_column(DateTime, server_default=func.now())


class IndexStatus(Base):
    __tablename__ = "index_status"

    id: Mapped[int]              = mapped_column(primary_key=True)
    repo_name: Mapped[str]       = mapped_column(String(256), unique=True)
    last_indexed: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    file_count: Mapped[int]      = mapped_column(default=0)
    chunk_count: Mapped[int]     = mapped_column(default=0)
    status: Mapped[str]          = mapped_column(String(64), default="pending")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
