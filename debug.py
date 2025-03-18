#!/usr/bin/env python3
"""
Debug script to check system setup and diagnose common issues.
"""
import sys
import os
import platform
import sqlite3
import importlib
import subprocess
from pathlib import Path

def check_python():
    print(f"Python version: {platform.python_version()}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    
def check_imports():
    print("\nChecking required modules:")
    modules = [
        "logging", "threading", "sqlite3", "email", "pathlib", "json",
        "time", "webbrowser", "argparse", "shutil", "hashlib", "re"
    ]
    
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
    
    # Check optional modules
    print("\nChecking optional modules:")
    optionals = ["chardet", "psutil", "pytz"]
    
    for module in optionals:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e} (optional)")

def check_files():
    print("\nChecking essential files:")
    required_files = [
        "main.py", "email_processor.py", "database.py", "thread_utils.py", 
        "email_parser.py", "exceptions.py", "config.py", "utils.py",
        "ui_manager.py"
    ]
    
    for filename in required_files:
        filepath = Path(filename)
        if filepath.exists():
            print(f"✓ {filename} ({filepath.stat().st_size} bytes)")
        else:
            print(f"✗ {filename} (MISSING)")

def check_database():
    print("\nChecking database:")
    try:
        # Try to import config for database path
        try:
            import config
            db_path = config.DATABASE_FILE
            print(f"Database path from config: {db_path}")
        except (ImportError, AttributeError):
            db_path = "emails.db"
            print(f"Using default database path: {db_path}")
        
        db_file = Path(db_path)
        if db_file.exists():
            print(f"✓ Database file exists ({db_file.stat().st_size} bytes)")
            
            # Try to open the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"✓ Found {len(tables)} tables: {', '.join(t[0] for t in tables)}")
            
            # Check email count
            try:
                cursor.execute("SELECT COUNT(*) FROM emails;")
                count = cursor.fetchone()[0]
                print(f"✓ Database contains {count} emails")
            except sqlite3.OperationalError:
                print("✗ Could not count emails (table may not exist)")
            
            conn.close()
        else:
            print(f"✗ Database file does not exist")
    except Exception as e:
        print(f"✗ Database check failed: {e}")

def attempt_fix():
    print("\nAttempting to fix common issues:")
    
    # Create thread_utils.py if missing
    if not Path("thread_utils.py").exists():
        try:
            print("Creating missing thread_utils.py with basic implementation")
            with open("thread_utils.py", "w") as f:
                f.write('''"""
Utilities for identifying and managing email threads.
"""

import re
import logging
from typing import Dict, Any, Optional, Set, List
import hashlib

logger = logging.getLogger(__name__)

class ThreadIdentifier:
    def __init__(self):
        self.threads = {}
        self.subject_threads = {}
        self.reference_map = {}
        self.next_thread_id = 1
        
    def get_thread_count(self) -> int:
        return len(self.threads)
        
    def identify_thread(self, email: Dict[str, Any]) -> Optional[str]:
        if not email:
            return None
            
        message_id = email.get('message_id')
        if not message_id:
            return None
            
        # Check if this message is already in a thread
        if message_id in self.reference_map:
            return self.reference_map[message_id]
        
        # Create a simple thread ID
        thread_id = f"thread-{self.next_thread_id}"
        self.next_thread_id += 1
        self.reference_map[message_id] = thread_id
        return thread_id
''')
            print("✓ Created thread_utils.py")
        except Exception as e:
            print(f"✗ Failed to create thread_utils.py: {e}")
    
    # Update imports in email_processor.py if needed
    try:
        with open("email_processor.py", "r") as f:
            content = f.read()
        
        if "from database import" in content and "update_thread_info" not in content:
            print("Fixing import in email_processor.py")
            content = content.replace(
                "from database import insert_email_data",
                "from database import insert_email_data, update_thread_info"
            )
            with open("email_processor.py", "w") as f:
                f.write(content)
            print("✓ Updated imports in email_processor.py")
    except Exception as e:
        print(f"✗ Failed to fix email_processor.py: {e}")

def run_program():
    print("\nTrying to run main.py:")
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("Output:", result.stdout[:500] + ("..." if len(result.stdout) > 500 else ""))
        if result.stderr:
            print("Errors:", result.stderr[:500] + ("..." if len(result.stderr) > 500 else ""))
    except Exception as e:
        print(f"Error running main.py: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("STONE EMAIL & IMAGE PROCESSOR - DIAGNOSTIC TOOL")
    print("=" * 60)
    
    check_python()
    check_imports()
    check_files()
    check_database()
    
    print("\nWould you like to attempt automatic fixes? (y/n)")
    choice = input().lower()
    if choice.startswith('y'):
        attempt_fix()
        print("\nWould you like to try running the program now? (y/n)")
        choice = input().lower()
        if choice.startswith('y'):
            run_program()
    
    print("\nDiagnostic complete. If problems persist, please check the log files")
    print("or report the issue with the information above.")
