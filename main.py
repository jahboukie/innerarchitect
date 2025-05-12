from app import app  # noqa: F401
from logging_config import get_logger, info

# Get module-specific logger
logger = get_logger('main')

if __name__ == "__main__":
    logger.info("Starting The Inner Architect application")
    app.run(host="0.0.0.0", port=5000, debug=True)
