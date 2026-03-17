import logging
import logging.config
import os

# Modifica per PROFETA 5.0
import os
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if LOG_DIR is None:
    LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "cfx_client.log")

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
        "detailed": {
            "format": "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": LOG_FILE,
            "when": "midnight",
            "interval": 1,
            "backupCount": 14,
            "encoding": "utf8",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console", "file"]},
}

# Apply logging configuration
logging.config.dictConfig(LOGGING_CONFIG)


# Function to get a logger
def get_logger(name):
    return logging.getLogger(name)
