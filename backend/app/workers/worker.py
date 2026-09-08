from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import process_document


class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    queue_name = get_settings().arq_queue_name
    max_jobs = 4
    job_timeout = 600
    keep_result = 3600
