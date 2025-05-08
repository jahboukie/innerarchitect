from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Define base class for models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)