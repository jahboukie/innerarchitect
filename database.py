from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from logging_config import get_logger

# Get module-specific logger
logger = get_logger('database')

# Define base class for models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

logger.debug("SQLAlchemy database instance initialized")