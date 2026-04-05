import logging
from logging import FileHandler, StreamHandler
from pathlib import Path

from app.config import settings


def configure_logging(service_name: str) -> None:
    handlers: list[logging.Handler] = [StreamHandler()]

    if settings.DEBUG:
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(FileHandler(log_dir / f"{service_name}.log"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )

    app_level = logging.DEBUG if settings.DEBUG else logging.INFO
    for logger_name in ("app", "worker", "tests", service_name):
        logging.getLogger(logger_name).setLevel(app_level)
