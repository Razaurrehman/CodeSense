import uuid as _uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import String, Text, DateTime, Integer, func
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


class ScanResult(Base):
    __tablename__ = "scan_results"

    id:              Mapped[int]      = mapped_column(primary_key=True)
    repo_name:       Mapped[str]      = mapped_column(String(256))
    task:            Mapped[str]      = mapped_column(String(64))
    total_findings:  Mapped[int]      = mapped_column(Integer, default=0)
    critical:        Mapped[int]      = mapped_column(Integer, default=0)
    high:            Mapped[int]      = mapped_column(Integer, default=0)
    medium:          Mapped[int]      = mapped_column(Integer, default=0)
    low:             Mapped[int]      = mapped_column(Integer, default=0)
    output:          Mapped[str]      = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id:               Mapped[int]      = mapped_column(primary_key=True)
    uuid:             Mapped[str]      = mapped_column(String(36), unique=True, default=lambda: str(_uuid.uuid4()))
    repo_name:        Mapped[str]      = mapped_column(String(256))
    repo_url:         Mapped[str]      = mapped_column(String(512))
    scan_types:       Mapped[str]      = mapped_column(Text)           # JSON array of user_story strings
    status:           Mapped[str]      = mapped_column(String(32), default="queued")  # queued|running|done|failed
    total_scans:      Mapped[int]      = mapped_column(Integer, default=0)
    completed_scans:  Mapped[int]      = mapped_column(Integer, default=0)
    pr_number:        Mapped[int]      = mapped_column(Integer, nullable=True)
    pdf_path:         Mapped[str]      = mapped_column(String(512), nullable=True)
    error:            Mapped[str]      = mapped_column(Text, nullable=True)
    created_at:       Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at:     Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ScanJobResult(Base):
    __tablename__ = "scan_job_results"

    id:         Mapped[int] = mapped_column(primary_key=True)
    job_id:     Mapped[int] = mapped_column(Integer, index=True)
    scan_type:  Mapped[str] = mapped_column(String(64))
    status:     Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|failed
    output:     Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
