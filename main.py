#!/usr/bin/env python3
"""
Stone Email Processor main application
"""
import sys
import os
import time
import traceback

# Super early debugging - before any imports
with open("/tmp/stone_init.log", "w") as f:
    f.write(f"Starting application at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Working directory: {os.getcwd()}\n")

print("Starting Stone Email Processor...")
print(f"Current directory: {os.getcwd()}")

# Import core modules with verbose error handling
try:
    import logging
    from pathlib import Path
    print("Successfully imported basic modules")
except Exception as e:
    error_msg = f"ERROR importing basic modules: {str(e)}"
    print(error_msg)
    with open("/tmp/stone_init_error.log", "w") as f:
        f.write(error_msg + "\n")
        f.write(traceback.format_exc())
    sys.exit(1)

# Import application modules with verbose error handling
try:
    print("Importing application modules...")
    import config
    print(f"Config loaded. Version: {config.VERSION}")
    from database import create_database
    from email_processor import process_mbox_files
    from image_processor import process_image_files
    from pdf_processor import process_pdf_files
    from ui_manager import start_ui_server, open_ui_in_browser
    from argparse import ArgumentParser
    from utils import (
        setup_logging, backup_database,
        load_file_cache, save_file_cache, display_statistics,
        ensure_data_directory, identify_unsupported_files
    )
    print("All application modules imported successfully")
except Exception as e:
    error_msg = f"ERROR importing application modules: {str(e)}"
    print(error_msg)
    with open("/tmp/stone_init_error.log", "w") as f:
        f.write(error_msg + "\n")
        f.write(traceback.format_exc())
    sys.exit(1)

def parse_args():
    """
    Parse command line arguments for the application.
    """
    parser = ArgumentParser(description="Process email, image, and PDF files and insert data into the database.")
    parser.add_argument("--directory", "-d", 
                       help=f"Directory containing files to process (emails, images, PDFs). Default: {config.MBOX_DIRECTORY}", 
                       type=str, default=config.MBOX_DIRECTORY)
    parser.add_argument("--log-level", help="Override logging level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=None)
    parser.add_argument("--backup", help="Create a backup of the database before processing", action="store_true")
    parser.add_argument("--batch-size", help="Number of emails to process in a single batch", type=int, default=1000)
    parser.add_argument("--version", help="Show version information and exit", action="store_true")
    parser.add_argument("--skip-emails", help="Skip processing email files", action="store_true")
    parser.add_argument("--skip-images", help="Skip processing image files", action="store_true")
    parser.add_argument("--skip-pdfs", help="Skip processing PDF files", action="store_true")
    parser.add_argument("--no-ui", help="Don't open UI when processing completes", action="store_true")
    parser.add_argument("--port", help="Port for the UI server", type=int, default=config.UI_PORT)
    parser.add_argument("--query", "-q", help="Run SQL query and display results", type=str, default=None)
    parser.add_argument("--output", "-o", help="Output file for query results (CSV format)", type=str, default=None)
    return parser.parse_args()

def main() -> int:
    """
    Main orchestrator for the email and image processing application.
    
    Returns:
        int: 0 on success, non-zero on error
    """
    # Direct console output for immediate feedback
    print(f"Stone Email Processor v{config.VERSION} starting...")
    
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
    input_dir = Path(args.directory)
    
    # Ensure the data directory exists and is properly set up
    ensure_data_directory(input_dir)
    
    if not input_dir.exists():
        try:
            input_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {input_dir}")
        except Exception as e:
            print(f"Error creating directory '{input_dir}': {e}")
            return 1
    elif not input_dir.is_dir():
        print(f"Error: '{input_dir}' exists but is not a directory")
        return 1
    
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    logger = setup_logging()
    
    # Override UI port if specified
    if args.port != config.UI_PORT:
        config.UI_PORT = args.port
    
    # Set the root logger to use our logger configuration
    root_logger = logging.getLogger()
    for handler in logger.handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(logger.level)
    
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

    # Log environment information for debugging
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Database path: {config.DATABASE_FILE}")
    logger.info(f"Input directory: {input_dir}")

    try:
        # Ensure database exists
        create_database(str(db_path))
        logger.info(f"Database ready at {db_path}")
    except Exception as e:
        logger.exception(f"Failed to create or access the database: {e}")
        return 1

    metrics = {"start_time": start_time, "processed_files": 0, "processed_emails": 0}
    
    # Start UI server early so it can show progress
    try:
        server, _ = start_ui_server(metrics, logger, str(db_path))
    except Exception as e:
        logger.exception(f"Failed to start UI server: {e}")
        # Continue without UI
        server = None
    
    if args.query:
        try:
            from database_query import execute_query_command
            execute_query_command(args.query, output_file=args.output, logger=logger)
            # Exit after query execution if not running a query
            return 0
        except ImportError:
            logger.error("The 'database_query' module could not be found. Ensure 'database_query.py' exists and is accessible.")
            return 1
    
    if args.backup:
        if not backup_database(logger):
            logger.error("Database backup failed, aborting")
            return 1
    
    # Ensure data directory is fully accessible
    try:
        # Test write access to data directory
        test_file = input_dir / ".test_access"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"Confirmed write access to data directory: {input_dir}")
    except Exception as e:
        logger.error(f"Cannot write to data directory {input_dir}: {e}")
        print(f"Error: Cannot write to data directory {input_dir}")
        print("Please check directory permissions and try again.")
        return 1
    
    exit_code = 0
    
    try:
        # Process email files
        if not args.skip_emails:
            print(f"Looking for .mbox files in: {input_dir}")
            logger.info("Starting email processing...")
            logger.info(f"Looking for .mbox files in: {input_dir}")
            
            # Enhanced MBOX file detection with more diagnostic info
            mbox_files = list(input_dir.glob('*.mbox')) + list(input_dir.glob('*.MBOX'))
            all_files = list(input_dir.iterdir())
            logger.info(f"Directory contains {len(all_files)} total files")
            
            if not mbox_files:
                # Direct console warning
                print(f"⚠️ Warning: No .mbox files found in {input_dir}")
                
                # Log more detailed information to help diagnose why no MBOX files are found
                logger.warning(f"No .mbox files found in directory: {input_dir} (absolute path: {input_dir.absolute()})")
                logger.info(f"Directory content sample (up to 10 files): {[f.name for f in all_files[:10]]}")
                metrics["warning"] = "No .mbox files found in input directory"
            else:
                found_msg = f"Found {len(mbox_files)} .mbox files to process"
                print(found_msg)
                logger.info(f"{found_msg}: {[f.name for f in mbox_files]}")
                metrics["mbox_files_found"] = len(mbox_files)
            
            try:
                email_exit_code = process_mbox_files(
                    str(input_dir),  # Convert Path to string for compatibility
                    logger,
                    batch_size=args.batch_size,
                    metrics=metrics
                )
                if email_exit_code != 0:
                    logger.error(f"Email processing failed with exit code: {email_exit_code}")
                    exit_code = email_exit_code
            except Exception as e:
                logger.exception(f"Exception during email processing: {e}")
                exit_code = 1
        
        # Process image files
        if not args.skip_images and config.IMAGE_PROCESSING_ENABLED:
            logger.info("Starting image processing...")
            image_exit_code = process_image_files(
                str(input_dir),
                logger,
                metrics=metrics
            )
            if image_exit_code != 0 and exit_code == 0:
                exit_code = image_exit_code
        
        # Process PDF files
        if not args.skip_pdfs and config.DOCUMENT_PROCESSING_ENABLED:
            logger.info("Starting PDF processing...")
            pdf_exit_code = process_pdf_files(
                str(input_dir),
                logger,
                metrics=metrics
            )
            if pdf_exit_code != 0 and exit_code == 0:
                exit_code = pdf_exit_code
        
        # Identify and report unsupported files
        unsupported_files = identify_unsupported_files(str(input_dir), logger)
        metrics["unsupported_files"] = unsupported_files
        
        if unsupported_files:
            logger.warning(f"Found {len(unsupported_files)} unsupported files in {input_dir}")
            for file_info in unsupported_files[:10]:  # Show first 10 only to avoid log spam
                logger.warning(f"Unsupported file: {file_info['name']} ({file_info['extension']})")
            
            if len(unsupported_files) > 10:
                logger.warning(f"... and {len(unsupported_files) - 10} more unsupported files")
        
        # Use detailed=False to prefer UI for detailed statistics
        display_statistics(logger, metrics, detailed=False)
        
        # Check database stats before opening UI
        try:
            from database_query import get_database_stats
            db_stats = get_database_stats(logger)
            logger.info(f"Database statistics: {db_stats}")
            if db_stats.get('total_emails', 0) == 0:
                logger.warning("Database contains no emails. UI may not display any data.")
        except Exception as e:
            logger.warning(f"Failed to get database statistics: {e}")
        
        if not args.no_ui:
            # Enhanced UI opening with better error handling
            logger.info("Attempting to open UI in browser...")
            try:
                ui_success = open_ui_in_browser(logger)
                if ui_success:
                    logger.info("UI successfully opened in browser")
                else:
                    logger.warning("Failed to open UI in browser, but server is running")
                logger.info(f"UI server is running at http://localhost:{config.UI_PORT}. Press Ctrl+C to exit.")
            except Exception as e:
                logger.exception(f"Failed to open UI in browser: {e}")
                logger.info(f"You can manually access the UI at http://localhost:{config.UI_PORT}")
        
            # Keep the server running so you can view results
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down UI server...")
                if server:
                    server.shutdown()
                    server.server_close()
        
        return exit_code
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        if server:
            server.shutdown()
            server.server_close()
        return 130
    except Exception as e:
        logger.exception(f"Failed during processing: {e}")
        if 'server' in locals() and server:
            try:
                server.shutdown()
                server.server_close()
            except:
                pass
        return 1

if __name__ == "__main__":
    # First thing - verify basic output capability
    try:
        print("STARTUP: Stone Email Processor")
        sys.stdout.write("STARTUP: Testing direct stdout write\n")
        sys.stdout.flush()
    except Exception as e:
        # Try to write to a file if console output fails
        with open("/tmp/stone_error.log", "w") as f:
            f.write(f"Console output error: {str(e)}\n")

    # Force stdout buffer to flush regularly
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)
    except Exception:
        pass
    
    # Capture uncaught exceptions
    try:
        print("Calling main() function...")
        exit_code = main()
        print(f"Main function completed with exit code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        error_msg = f"FATAL UNCAUGHT EXCEPTION: {str(e)}\n{traceback.format_exc()}"
        
        # Try multiple error reporting methods
        try:
            print(error_msg, file=sys.stderr)
        except:
            pass
            
        try:
            with open("/tmp/stone_crash.log", "w") as f:
                f.write(error_msg)
        except:
            pass
            
        sys.exit(1)