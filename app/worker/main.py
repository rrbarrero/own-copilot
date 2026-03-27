import asyncio
import logging
import signal

from app.infra.db import get_db_pool
from app.ingestion.application.worker_service import IngestionWorker
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")


async def main():
    pool = get_db_pool()
    await pool.open()

    job_repo = PostgresJobRepo(pool)
    worker = IngestionWorker(job_repo)

    # Signal handling
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    try:
        await worker.run()
    finally:
        await pool.close()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
