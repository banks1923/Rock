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
    parser.add_argument("--quiet", help="Suppress console output", action="store_true")
    parser.add_argument("--dry-run", help="Process files without modifying the database", action="store_true")
    parser.add_argument("--workers", help="Number of parallel workers for processing", type=int, default=1)
    parser.add_argument("--version", help="Show version information and exit", action="store_true")
    parser.add_argument("--skip-unchanged", help="Skip processing files that haven't changed since the last run", action="store_true")
    parser.add_argument("--backup", help="Create a backup of the database before processing", action="store_true")
    parser.add_argument("--max-memory", help="Maximum memory usage in percentage", type=int, default=80)
    parser.add_argument("--batch-size", help="Number of emails to process in a single batch", type=int, default=1000)
    parser.add_argument("--stats-only", help="Only display statistics without processing files", action="store_true")
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
    
    if args.quiet:
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

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
    
    if args.backup and not args.dry_run and not args.stats_only:
        if not backup_database(logger):
            logger.error("Database backup failed, aborting")
            return 1
    
    file_cache = {}
    if args.skip_unchanged:
        file_cache = load_file_cache()
        logger.info(f"Loaded cache with {len(file_cache)} previously processed files")
    
    if args.stats_only:
        logger.info("Stats-only mode requested, displaying previous run statistics")
        display_statistics(logger, metrics)
        return 0
    
    try:
        if args.dry_run:
            logger.info("Running in dry-run mode - no database changes will be made")
        
        # Process the files
        exit_code = process_mbox_files(
            str(mbox_dir),  # Convert Path to string for compatibility
            logger, 
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            file_cache=file_cache if args.skip_unchanged else None,
            max_memory_pct=args.max_memory,
            metrics=metrics
        )
        
        if args.skip_unchanged and file_cache:
            save_file_cache(file_cache)
            
        display_statistics(logger, metrics)
        
        return exit_code
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        if args.skip_unchanged and file_cache:
            save_file_cache(file_cache)
        return 130
    except Exception as e:
        logger.exception(f"Failed during mbox file processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())