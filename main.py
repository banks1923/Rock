import sys
import logging
import time
from pathlib import Path
import config
from database import create_database
from email_processor import process_mbox_files
from argparse import ArgumentParser
from utils import (
    setup_logging, backup_database,
    load_file_cache, save_file_cache, display_statistics
)

def parse_args():
    """
    Parse command line arguments for the application.
    """
    parser = ArgumentParser(description="Process .mbox files and insert email data into the database.")
    parser.add_argument("--directory", "-d", help=f"Directory containing .mbox files (default: {config.MBOX_DIRECTORY})", 
                        type=str, default=config.MBOX_DIRECTORY)
    parser.add_argument("--log-level", help="Override logging level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=None)
    parser.add_argument("--backup", help="Create a backup of the database before processing", action="store_true")
    parser.add_argument("--batch-size", help="Number of emails to process in a single batch", type=int, default=1000)
    parser.add_argument("--version", help="Show version information and exit", action="store_true")
    return parser.parse_args()

def main() -> int:
    """
    Main orchestrator for the email processing application.
    
    Returns:
        int: 0 on success, non-zero on error
    """
    start_time = time.time()
    
    try:
        args = parse_args()
    except SystemExit as e:
        # Handle argument parsing errors more gracefully
        if e.code != 0:
            print("Error: Invalid command line arguments")
            print("Use --help for usage information")
        return int(e.code) if e.code is not None else 1
    
    if args.version:
        print(f"Stone Email Processor v{config.VERSION}")
        return 0
    
    # Create directory if it doesn't exist using pathlib
    mbox_dir = Path(args.directory)
    if not mbox_dir.exists():
        try:
            mbox_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {mbox_dir}")
        except Exception as e:
            print(f"Error creating directory '{mbox_dir}': {e}")
            return 1
    elif not mbox_dir.is_dir():
        print(f"Error: '{mbox_dir}' exists but is not a directory")
        return 1
    
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    logger = setup_logging()
    
    # Ensure database directory exists
    db_path = Path(config.DATABASE_FILE)
    db_dir = db_path.parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            return 1

    if not db_path.exists():
        try:
            create_database(str(db_path))
            logger.info(f"Created database at {db_path}")
        except Exception as e:
            logger.exception(f"Failed to create or access the database: {e}")
            return 1

    metrics = {"start_time": start_time, "processed_files": 0, "processed_emails": 0}
    
    if args.backup:
        if not backup_database(logger):
            logger.error("Database backup failed, aborting")
            return 1
    
    try:
        # Process the files
        exit_code = process_mbox_files(
            str(mbox_dir),  # Convert Path to string for compatibility
            logger, 
            batch_size=args.batch_size,
            metrics=metrics
        )
        
        display_statistics(logger, metrics)
        
        return exit_code
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Failed during mbox file processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())