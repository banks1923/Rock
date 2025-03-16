import sys
import logging
import os
import time
import hashlib
import json
import shutil
import psutil
import config
from pathlib import Path

def setup_logging() -> logging.Logger:
    """
    Sets up logging with both file and console handlers.
    """
    logger = logging.getLogger(__name__)
    if logger.hasHandlers():
        return logger

    log_dir = os.path.dirname(config.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def get_file_hash(file_path):
    """
    Calculate SHA256 hash of a file to detect changes.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def backup_database(logger):
    """
    Create a backup of the database file.
    """
    if not os.path.exists(config.DATABASE_FILE):
        logger.warning("No database file exists to backup")
        return True
        
    backup_path = f"{config.DATABASE_FILE}.{int(time.time())}.bak"
    try:
        shutil.copy2(config.DATABASE_FILE, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False

def check_memory_usage(max_percentage, logger):
    """
    Check if memory usage is below the specified threshold.
    """
    usage = psutil.virtual_memory().percent
    if usage > max_percentage:
        logger.warning(f"Memory usage at {usage}% exceeds threshold of {max_percentage}%")
        return False
    return True

def load_file_cache():
    """
    Load the cache of processed files and their hashes.
    Uses a more memory-efficient approach for large caches.
    """
    cache_path = Path(os.path.dirname(config.DATABASE_FILE)) / "processed_files.json"
    
    if not cache_path.exists():
        return {}
        
    try:
        # Use 'r' mode with explicit encoding for better compatibility
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger = logging.getLogger(__name__)
        logger.warning(f"Invalid JSON in cache file {cache_path}, rebuilding cache")
        return {}
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading cache file: {e}")
        return {}

def save_file_cache(cache_data):
    """
    Save the cache of processed files and their hashes.
    Implements safe writing to prevent corruption.
    """
    cache_path = Path(os.path.dirname(config.DATABASE_FILE)) / "processed_files.json"
    temp_path = cache_path.with_suffix('.tmp')
    
    try:
        # First write to a temporary file
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
            
        # Then rename it to the actual file (atomic operation on most systems)
        temp_path.replace(cache_path)
        
        logger = logging.getLogger(__name__)
        logger.debug(f"Cache saved with {len(cache_data)} entries")
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving cache: {e}")
        return False

def display_statistics(logger, metrics):
    """
    Display processing statistics.
    """
    execution_time = time.time() - metrics["start_time"]
    logger.info("=" * 50)
    logger.info("Processing Statistics:")
    logger.info(f"- Files processed: {metrics['processed_files']}")
    logger.info(f"- Emails processed: {metrics['processed_emails']}")
    
    if metrics["processed_emails"] > 0 and execution_time > 0:
        emails_per_second = metrics["processed_emails"] / execution_time
        logger.info(f"- Processing speed: {emails_per_second:.2f} emails/second")
    
    logger.info(f"- Total execution time: {execution_time:.2f} seconds")
    logger.info("=" * 50)
