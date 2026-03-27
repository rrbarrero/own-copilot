import asyncio
import logging
import signal

from app.factory import create_job_repo, get_db_pool
from app.ingestion.application.worker_service import IngestionWorker
from app.worker.factory import create_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")


async def main():
    pool = get_db_pool()
    await pool.open()

    # 1. Initialize dependencies using factories
    job_repo = create_job_repo()
    pipeline = create_pipeline()

    # 2. Setup worker
    worker = IngestionWorker(job_repo=job_repo, pipeline=pipeline)

    # 3. Signal handling
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    logger.info("Worker is ready to process jobs")

    try:
        await worker.run()
    finally:
        await pool.close()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
