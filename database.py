from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, Optional, TypeVar, Type, List, Union, Callable
from logging_config import get_logger, error, debug, warning, info

# Get module-specific logger
logger = get_logger('database')

# Define base class for models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

# Type variable for SQLAlchemy models
T = TypeVar('T', bound=Base)

def safe_commit() -> bool:
    """
    Safely commit changes to the database with error handling.
    
    Returns:
        bool: Success or failure
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        error(f"Database commit error: {str(e)}")
        db.session.rollback()
        return False
    except Exception as e:
        error(f"Unexpected error during database commit: {str(e)}")
        db.session.rollback()
        return False

def create_model(model_class: Type[T], data: Dict[str, Any]) -> Optional[T]:
    """
    Create a new model instance with error handling.
    
    Args:
        model_class: The SQLAlchemy model class
        data: Dictionary of model attributes
        
    Returns:
        The created model instance or None if failed
    """
    try:
        # Create model instance
        instance = model_class()
        
        # Set attributes manually to avoid constructor issues
        for key, value in data.items():
            setattr(instance, key, value)
            
        # Add to session
        db.session.add(instance)
        
        # Commit changes
        if safe_commit():
            return instance
        return None
    except Exception as e:
        error(f"Error creating {model_class.__name__}: {str(e)}")
        db.session.rollback()
        return None

def update_model(instance: T, data: Dict[str, Any]) -> bool:
    """
    Update a model instance with error handling.
    
    Args:
        instance: The model instance to update
        data: Dictionary of attributes to update
        
    Returns:
        bool: Success or failure
    """
    try:
        # Update attributes
        for key, value in data.items():
            setattr(instance, key, value)
            
        # Commit changes
        return safe_commit()
    except Exception as e:
        error(f"Error updating {type(instance).__name__}: {str(e)}")
        db.session.rollback()
        return False

def safe_query(
    model_class: Type[T], 
    filter_func: Optional[Callable] = None
) -> List[T]:
    """
    Safely execute a query with error handling.
    
    Args:
        model_class: The SQLAlchemy model class
        filter_func: Optional function to apply filters to the query
        
    Returns:
        List of model instances or empty list if failed
    """
    try:
        query = db.session.query(model_class)
        if filter_func:
            query = filter_func(query)
        return query.all()
    except Exception as e:
        error(f"Error querying {model_class.__name__}: {str(e)}")
        return []

logger.debug("SQLAlchemy database instance initialized with helper functions")