from __future__ import annotations

import logging
import os
import secrets


LOGGER_NAME = "labcim_manager"
logger = logging.getLogger(LOGGER_NAME)


def configure_logging() -> None:
    level_name = os.environ.get("APP_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def safe_exception_message(
    exc: BaseException,
    *,
    context: str,
    user_message: str = "Não foi possível concluir a operação.",
) -> str:
    """Log diagnostic context and return a non-sensitive user-facing reference."""

    event_id = secrets.token_hex(6)
    logger.error(
        "Falha em %s [referência=%s]",
        context,
        event_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return f"{user_message} Referência: {event_id}. Contate o administrador se o problema persistir."
