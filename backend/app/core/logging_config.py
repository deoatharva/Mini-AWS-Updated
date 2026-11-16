import logging
from logging.config import dictConfig

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


def configure_logging() -> None:
    dictConfig(LOG_CONFIG)
    logging.getLogger(__name__).debug("Logging configured")
