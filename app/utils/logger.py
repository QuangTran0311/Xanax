import sys

from loguru import logger as _logger

from app.config import settings

_logger.remove()
_logger.add(
    sys.stdout,
    level="DEBUG" if settings.is_dev else "INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
    colorize=True,
)

logger = _logger
