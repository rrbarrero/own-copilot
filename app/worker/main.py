import asyncio
import logging
import signal

from app.infra.db import Database
from app.worker.factory import create_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")


async def main():
    pool = Database.get_pool()
    await pool.open()

    # 1. Setup worker using centralized factory
    worker = create_worker()

    # 2. Validate embedding dimension
    # (Checking if model matches DB schema)
    logger.info("Validating embedding dimension...")
    try:
        if worker.handlers.get("process_document"):
            from app.config import settings
            from app.worker.infrastructure.embeddings.ollama_embedding_service import (
                OllamaEmbeddingService,
            )

            embed_svc = OllamaEmbeddingService(
                model=settings.EMBEDDING_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
            model_dim = await embed_svc.get_dimension()
            db_dim = await Database.get_embedding_dimension()

            if db_dim != -1 and model_dim != db_dim:
                logger.critical(
                    f"Dimension mismatch! "
                    f"Model yields {model_dim}, but DB expects {db_dim}."
                )
                await Database.close()
                exit(1)
            logger.info(f"Embedding dimension validated: {model_dim}")
        else:
            logger.warning("No processing handler, skipping dimension check")
    except Exception as e:
        logger.error(f"Failed to validate embedding dimension: {e}")

    # 3. Signal handling
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    logger.info("Worker is ready to process jobs")

    try:
        await worker.run()
    finally:
        await Database.close()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
