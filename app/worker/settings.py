"""arq WorkerSettings — configure the Redis queue worker."""
from arq.connections import RedisSettings
from app.core.config import settings as app_settings
from app.worker.tasks import run_scan_job


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions     = [run_scan_job]
    redis_settings = RedisSettings.from_dsn(app_settings.redis_url)
    max_jobs      = 4       # concurrent scan jobs per worker instance
    job_timeout   = 7200    # 2-hour ceiling per job
    keep_result   = 86400   # keep arq metadata for 24 h
    retry_jobs    = True
    max_tries     = 2
    on_startup    = startup
    on_shutdown   = shutdown
