#!/usr/bin/env python3
"""
Functionality test script for Stone Email & Image Processor.
This script tests core functionality to help diagnose issues.
"""
import os
import sys
import sqlite3
import logging
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import email.message
import mailbox

# First, add the current directory to the path to ensure we can import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
try:
    import config
    from utils import setup_logging, get_file_hash
    from database import create_database, insert_email_data, update_thread_info
    from email_processor import process_mbox_files
    from thread_utils import ThreadIdentifier
    from ui_manager import start_ui_server
    logger.info("✅ Successfully imported all modules")
except ImportError as e:
    logger.error(f"❌ Error importing modules: {e}")
    sys.exit(1)

def create_test_directory():
    """Create a temporary directory for testing purposes."""
    try:
        test_dir = Path(tempfile.mkdtemp(prefix="stone_test_"))
        logger.info(f"✅ Created test directory: {test_dir}")
        return test_dir
    except Exception as e:
        logger.error(f"❌ Failed to create test directory: {e}")
        return None

def create_test_database(test_dir):
    """Create a test database and verify it works."""
    try:
        db_path = test_dir / "test.db"
        create_database(str(db_path))
        
        # Verify by connecting and checking tables
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        expected_tables = ["emails", "email_threads"]
        if all(table in tables for table in expected_tables):
            logger.info(f"✅ Test database created with tables: {', '.join(tables)}")
            return db_path
        else:
            logger.error(f"❌ Database missing expected tables. Found: {tables}")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create test database: {e}")
        return None

def create_test_mbox(test_dir):
    """Create a test mbox file with sample emails."""
    try:
        mbox_path = test_dir / "test.mbox"
        mb = mailbox.mbox(str(mbox_path))
        
        # Create a few sample emails
        for i in range(1, 4):
            msg = email.message.EmailMessage()
            msg["From"] = f"sender{i}@example.com"
            msg["To"] = "recipient@example.com"
            msg["Subject"] = f"Test Email {i}"
            msg["Date"] = email.utils.formatdate()
            msg["Message-ID"] = f"<test{i}@example.com>"
            msg.set_content(f"This is test email {i}")
            mb.add(msg)
        
        mb.close()
        
        # Verify mbox file exists and has content
        if mbox_path.exists() and mbox_path.stat().st_size > 0:
            logger.info(f"✅ Created test mbox file with 3 messages: {mbox_path}")
            return mbox_path
        else:
            logger.error(f"❌ Failed to verify test mbox file")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create test mbox file: {e}")
        return None

def test_database_operations(db_path):
    """Test database CRUD operations."""
    try:
        # Create test email data
        test_emails = [
            {
                'message_id': f'test{i}@example.com',
                'date': datetime.now(),
                'sender': f'sender{i}@example.com',
                'receiver': 'recipient@example.com',
                'subject': f'Test Email {i}',
                'content': f'This is test email {i}',
                'keywords': 'test'
            }
            for i in range(1, 4)
        ]
        
        # Test insertion
        inserted = insert_email_data(test_emails, str(db_path), batch_size=10)
        if inserted != 3:
            logger.error(f"❌ Expected to insert 3 emails, but inserted {inserted}")
            return False
            
        # Verify data was inserted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM emails")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count != 3:
            logger.error(f"❌ Expected 3 emails in database, but found {count}")
            return False
            
        logger.info("✅ Database operations test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Database operations test failed: {e}")
        return False

def test_thread_identification():
    """Test the thread identification functionality."""
    try:
        thread_id = ThreadIdentifier()
        
        # Create some sample emails
        email1 = {'message_id': '<abc123@example.com>', 'subject': 'Test Thread', 'content': 'Test content'}
        email2 = {'message_id': '<def456@example.com>', 'subject': 'Re: Test Thread', 'content': 'This is a reply'}
        
        # Identify threads
        thread_id1 = thread_id.identify_thread(email1)
        thread_id2 = thread_id.identify_thread(email2)
        
        if thread_id1 is None or not isinstance(thread_id1, str):
            logger.error(f"❌ Thread identification returned invalid ID: {thread_id1}")
            return False
            
        logger.info("✅ Thread identification test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Thread identification test failed: {e}")
        return False

def test_ui_server():
    """Test that the UI server can start."""
    try:
        metrics = {"start_time": time.time()}
        test_logger = logging.getLogger("test_ui")
        
        # Try to start the UI server
        server, thread = start_ui_server(metrics, test_logger)
        
        # If we got here without exception, shutdown the server and consider it a success
        if server:
            server.shutdown()
            logger.info("✅ UI server test passed - server started successfully")
            return True
        else:
            logger.error("❌ UI server test failed - server didn't start")
            return False
    except Exception as e:
        logger.error(f"❌ UI server test failed: {e}")
        return False

def test_email_processing(test_dir, db_path, mbox_path):
    """Test email processing functionality."""
    try:
        # Temporarily replace config.DATABASE_FILE with our test database
        original_db = config.DATABASE_FILE
        config.DATABASE_FILE = str(db_path)
        
        # Process the test mbox file
        metrics = {"start_time": time.time()}
        result = process_mbox_files(
            str(test_dir),
            logger,
            batch_size=10,
            metrics=metrics
        )
        
        # Restore the original database path
        config.DATABASE_FILE = original_db
        
        # Check if processing was successful
        if result != 0:
            logger.error(f"❌ Email processing test failed with code: {result}")
            return False
            
        # Verify emails were processed
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM emails")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count < 3:  # We should have at least the 3 from our test mbox
            logger.error(f"❌ Expected at least 3 emails processed, but found {count}")
            return False
            
        logger.info(f"✅ Email processing test passed - processed {count} emails")
        return True
    except Exception as e:
        logger.error(f"❌ Email processing test failed: {e}")
        # Restore the original database path
        config.DATABASE_FILE = original_db if 'original_db' in locals() else config.DATABASE_FILE
        return False

def cleanup(test_dir):
    """Clean up test resources."""
    try:
        if test_dir and test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info(f"✅ Cleaned up test directory: {test_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to clean up test directory: {e}")

def run_all_tests():
    """Run all functionality tests."""
    logger.info("=" * 50)
    logger.info("Starting functionality tests")
    logger.info("=" * 50)
    
    # Keep track of test results
    results = {
        "setup": False,
        "database": False,
        "thread": False,
        "ui_server": False,
        "email_processing": False
    }
    
    # Create test environment
    test_dir = create_test_directory()
    if not test_dir:
        logger.error("❌ Test setup failed. Cannot continue.")
        return False
        
    results["setup"] = True
    
    try:
        # Test database functionality
        db_path = create_test_database(test_dir)
        if not db_path or not test_database_operations(db_path):
            logger.error("❌ Database functionality test failed")
        else:
            results["database"] = True
        
        # Test thread identification
        results["thread"] = test_thread_identification()
        
        # Test UI server
        results["ui_server"] = test_ui_server()
        
        # Test email processing
        mbox_path = create_test_mbox(test_dir)
        if db_path and mbox_path:
            results["email_processing"] = test_email_processing(test_dir, db_path, mbox_path)
        else:
            logger.error("❌ Email processing test skipped due to setup failures")
    finally:
        # Clean up test resources
        cleanup(test_dir)
    
    # Display summary
    logger.info("=" * 50)
    logger.info("Test Summary:")
    logger.info("-" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("-" * 50)
    logger.info(f"Overall: {passed}/{total} tests passed")
    logger.info("=" * 50)
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
