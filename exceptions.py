import logging

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass

class EmailParsingError(Exception):
    """Custom exception for email parsing errors."""
    pass