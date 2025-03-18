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
from typing import List, Dict, Any

def setup_logging() -> logging.Logger:
    """
    Sets up logging with both file and console handlers.
    """
    # Use root logger for application-wide logging
    logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    log_dir = os.path.dirname(config.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    try:
        file_handler = logging.FileHandler(config.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")
        # Continue without file logging

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set module loggers to use the root logger's level
    logging.getLogger('email_processor').setLevel(log_level)
    logging.getLogger('database').setLevel(log_level)
    logging.getLogger('thread_utils').setLevel(log_level)

    return logger

def get_file_hash(file_path):
    """
    Calculate SHA256 hash of a file to detect changes.
    Optimizes for large files using memory-mapped file reading.
    """
    sha256 = hashlib.sha256()
    file_size = os.path.getsize(file_path)
    threshold = 10 * 1024 * 1024  # Use mmap if file is larger than 10 MB
    if file_size > threshold:
        with open(file_path, 'rb') as f:
            import mmap
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                sha256.update(mm)
    else:
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
    """Display processing statistics."""
    elapsed_time = time.time() - metrics["start_time"]
    logger.info("=" * 50)
    logger.info("Processing Statistics:")
    logger.info(f"Total processing time: {elapsed_time:.2f} seconds")
    
    if "processed_emails" in metrics:
        logger.info(f"Processed emails: {metrics.get('processed_emails', 0)}")
    
    if "processed_files" in metrics:
        logger.info(f"Processed email files: {metrics.get('processed_files', 0)}")
    
    if "processed_images" in metrics:
        logger.info(f"Processed images: {metrics.get('processed_images', 0)}")
        
    if "processed_pdfs" in metrics:
        logger.info(f"Processed PDF files: {metrics.get('processed_pdfs', 0)}")
    
    if "unsupported_files" in metrics and metrics["unsupported_files"]:
        logger.info(f"Unsupported files: {len(metrics['unsupported_files'])}")
        
        # Group unsupported files by extension
        ext_counts = {}
        for file_info in metrics["unsupported_files"]:
            ext = file_info["extension"] or "no extension"
            if ext not in ext_counts:
                ext_counts[ext] = 0
            ext_counts[ext] += 1
        
        # Display extension counts
        logger.info("Unsupported file types:")
        for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {ext}: {count} file(s)")
    
    logger.info("=" * 50)

def ensure_data_directory(directory_path: Path) -> None:
    """
    Ensures the data directory exists and contains example README.txt file.
    
    Args:
        directory_path: Path to the data directory
    """
    # Create the directory if it doesn't exist
    directory_path.mkdir(parents=True, exist_ok=True)
    
    # Create a README.txt file with instructions if it doesn't exist
    readme_path = directory_path / "README.txt"
    if not readme_path.exists():
        with open(readme_path, 'w') as f:
            f.write("""DATA DIRECTORY
============

This directory is for files to be processed by the Stone Email & Image Processor.

Supported file types:
- Emails: .mbox, .eml files
- Images: .jpg, .jpeg, .png files
- Documents: .pdf files

Simply place your files in this directory and run the processor.
Results will be displayed in the web UI that opens automatically.

For more options, run with --help flag:
    python main.py --help
""")

def identify_unsupported_files(directory_path: str, logger: logging.Logger) -> List[Dict[str, str]]:
    """
    Identify files in the directory that aren't supported by any processor.
    
    Args:
        directory_path: Path to the directory containing files
        logger: Logger instance
    
    Returns:
        List of dictionaries with information about unsupported files
    """
    # Gather all supported extensions from config
    all_supported_exts = []
    for category, exts in config.SUPPORTED_EXTENSIONS.items():
        all_supported_exts.extend(exts)
    
    # Make sure all extensions are lowercase for case-insensitive comparison
    all_supported_exts = [ext.lower() for ext in all_supported_exts]
    
    unsupported_files = []
    directory = Path(directory_path)
    
    # Get all files in directory (excluding directories)
    try:
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.name != "README.txt":
                ext = file_path.suffix.lower()
                if ext not in all_supported_exts:
                    unsupported_files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "extension": ext,
                        "size": file_path.stat().st_size
                    })
    except Exception as e:
        logger.error(f"Error scanning directory for unsupported files: {e}")
    
    return unsupported_files
