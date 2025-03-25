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
    # Emergency debugging - write directly to a known file before any setup
    with open("/tmp/stone_debug.log", "w") as f:
        f.write(f"Startup diagnostic at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"sys.stdout type: {type(sys.stdout)}\n")
        f.write(f"sys.stderr type: {type(sys.stderr)}\n")
    
    # Print directly to ensure we have basic console output
    print("Initializing logging system...")
    print(f"sys.stdout appears to be: {type(sys.stdout)}")
    
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
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

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    simple_formatter = logging.Formatter('%(message)s')  # Simpler format for console

    try:
        file_handler = logging.FileHandler(config.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        print(f"Log file: {config.LOG_FILE}")  # Direct console output
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")
        # Continue without file logging

    # Use sys.stderr for critical/error/warning and sys.stdout for info/debug
    error_console = logging.StreamHandler(sys.stderr)
    error_console.setLevel(logging.WARNING)  # WARNING and above go to stderr
    error_console.setFormatter(formatter)
    logger.addHandler(error_console)

    info_console = logging.StreamHandler(sys.stdout)
    info_console.setLevel(logging.INFO)  # INFO and DEBUG go to stdout
    info_console.setFormatter(simple_formatter)
    info_console.addFilter(lambda record: record.levelno < logging.WARNING)  # Only handle INFO and DEBUG
    logger.addHandler(info_console)

    # Ensure we get some direct console output regardless of logging
    try:
        print(f"Direct print test: Starting Stone Email Processor v{config.VERSION}")
        original_stdout.write(f"Direct stdout write test: Log level: {config.LOG_LEVEL}\n")
        original_stdout.flush()
    except Exception as e:
        # If direct print fails, try writing to our emergency log
        with open("/tmp/stone_debug.log", "a") as f:
            f.write(f"Error during direct console output: {e}\n")
    
    print(f"Starting Stone Email Processor v{config.VERSION}")
    print(f"Log level: {config.LOG_LEVEL}")

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

def display_statistics(logger, metrics, detailed=False):
    """
    Display processing statistics in a consistent format.
    
    Args:
        logger: Logger instance
        metrics: Dictionary containing metrics about the processing
        detailed: Whether to show detailed statistics (defaults to False to prefer UI)
    """
    elapsed_time = time.time() - metrics.get("start_time", time.time())
    processed_files = metrics.get("processed_files", 0)
    processed_emails = metrics.get("processed_emails", 0)
    
    # Direct console output for critical information
    print("\n" + "=" * 50)
    print("PROCESSING SUMMARY")
    print("=" * 50)
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Files processed: {processed_files}")
    print(f"Emails processed: {processed_emails}")
    
    # Basic summary that's always shown
    logger.info("=" * 50)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    logger.info(f"Files processed: {processed_files}")
    logger.info(f"Emails processed: {processed_emails}")
    
    # Show warnings if any
    if "warning" in metrics:
        warning_msg = f"Warning: {metrics['warning']}"
        print(f"\n⚠️ {warning_msg}")
        logger.warning(warning_msg)
    
    # If mbox files were found but no emails processed, highlight this issue
    if metrics.get("mbox_files_found", 0) > 0 and processed_emails == 0:
        issue_msg = "IMPORTANT: MBOX files were found but no emails were processed. Check logs for errors."
        print(f"\n❌ {issue_msg}")
        logger.warning(issue_msg)
    
    # Show minimal UI access information
    ui_msg = f"For detailed statistics and visualization, visit the UI at: http://localhost:{config.UI_PORT}"
    print("\n" + "-" * 50)
    print(ui_msg)
    print("Press Ctrl+C to exit the server when done.")
    logger.info("-" * 50)
    logger.info(ui_msg)
    logger.info("Press Ctrl+C to exit the server when done.")
    
    # Only show detailed stats if specifically requested
    if detailed:
        print("\nDETAILED STATISTICS:")
        logger.info("-" * 50)
        logger.info("DETAILED STATISTICS:")
        
        # List all metrics except internal ones
        for key, value in sorted(metrics.items()):
            if key not in ["start_time", "warning", "unsupported_files"]:
                print(f"  {key}: {value}")
                logger.info(f"  {key}: {value}")
        
        # Show unsupported file count if available
        if "unsupported_files" in metrics and metrics["unsupported_files"]:
            print(f"  Unsupported files: {len(metrics['unsupported_files'])}")
            logger.info(f"  Unsupported files: {len(metrics['unsupported_files'])}")

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
