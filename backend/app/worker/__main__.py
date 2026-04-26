import logging

from redis import Redis
from rq import Connection, Queue, Worker

from ..config import settings
from ..logging_config import configure_logging


def main() -> None:
    configure_logging("worker")
    logging.getLogger("worker").info("starting worker redis_url=%s", settings.redis_url)
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        queues = [Queue("training"), Queue("admin")]
        worker = Worker(queues)
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
