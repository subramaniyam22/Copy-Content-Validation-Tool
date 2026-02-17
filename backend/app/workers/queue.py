"""Redis Queue (RQ) setup and connection."""
import redis
from rq import Queue
from app.config import settings

# Redis connection
redis_conn = redis.from_url(settings.REDIS_URL)

# Job queue
job_queue = Queue("validation", connection=redis_conn, default_timeout=1800)


def get_redis():
    """Get Redis connection for job progress tracking."""
    return redis_conn
