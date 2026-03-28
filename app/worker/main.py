import asyncio
import logging
import signal

from app.factory import get_db_pool
from app.worker.factory import create_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")


async def main():
    pool = get_db_pool()
    await pool.open()

    # 1. Setup worker using centralized factory
    worker = create_worker()

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
