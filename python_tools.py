#!/usr/bin/env python3
"""
Comprehensive debugging tool for Stone Email Processor
Usage:
    python debug_tools.py console     # Test console output methods
    python debug_tools.py runtime     # Check runtime environment
    python debug_tools.py run         # Force run main.py with output capture
    python debug_tools.py all         # Run all diagnostics
"""
import sys
import os
import io
import time
import logging
import traceback
import importlib
import subprocess
import argparse
import webbrowser

def test_console_output():
    """Test various console output methods."""
    print("\n===== CONSOLE OUTPUT TEST =====")
    print("Method 1: print() function")
    print("If you see this, print() works")
    
    time.sleep(0.2)
    
    print("\nMethod 2: sys.stdout.write()")
    sys.stdout.write("If you see this, sys.stdout.write() works\n")
    sys.stdout.flush()
    
    time.sleep(0.2)
    
    print("\nMethod 3: sys.stderr.write()")
    sys.stderr.write("If you see this, sys.stderr.write() works\n")
    sys.stderr.flush()
    
    time.sleep(0.2)
    
    print("\nMethod 4: os.system echo")
    os.system('echo "If you see this, os.system echo works"')
    
    print("\n===== CONSOLE TEST COMPLETE =====")

def check_runtime_environment():
    """Check Python environment, imports, and filesystem access."""
    print("\n===== RUNTIME ENVIRONMENT CHECK =====")
    
    # Python environment
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # stdout/stderr status
    print(f"sys.stdout type: {type(sys.stdout)}")
    print(f"sys.stderr type: {type(sys.stderr)}")
    print(f"sys.stdout is a tty: {sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else 'N/A'}")
    
    # Test basic logging
    print("\nTesting logging...")
    test_logger = logging.getLogger("test_logger")
    test_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    test_logger.addHandler(handler)
    test_logger.info("This is a test log message")
    
    # Test key module imports
    print("\nTesting module imports:")
    modules_to_test = ['config', 'utils', 'database', 'email_processor', 'ui_manager']
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            print(f"✗ {module_name}: {str(e)}")
    
    # Test file access
    print("\nTesting file access:")
    try:
        with open("test_output.txt", "w") as f:
            f.write("Test file write")
        print("✓ File write successful")
        os.remove("test_output.txt")
        print("✓ File delete successful")
    except Exception as e:
        print(f"✗ File access error: {e}")
    
    # Check config settings
    try:
        import config
        print(f"\nConfiguration:")
        print(f"Database: {config.DATABASE_FILE}")
        print(f"Log file: {config.LOG_FILE}")
        print(f"UI port: {config.UI_PORT}")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
    
    print("\n===== RUNTIME CHECK COMPLETE =====")

def test_ui_functionality():
    """Test UI server connectivity and database query functionality."""
    print("\n===== UI FUNCTIONALITY TEST =====")
    
    # Check if UI modules are available
    try:
        import config
        print(f"UI configuration: {config.UI_HOST}:{config.UI_PORT}")
    except ImportError:
        print("✗ Could not import config module")
        return
    
    # Test database direct access
    print("\nTesting direct database access:")
    try:
        import sqlite3
        import config
        
        # Connect directly to the database
        conn = sqlite3.connect(config.DATABASE_FILE)
        cursor = conn.cursor()
        
        # Get record count
        cursor.execute("SELECT COUNT(*) FROM emails")
        record_count = cursor.fetchone()[0]
        print(f"✓ Database connected successfully. Record count: {record_count}")
        
        # Test simple keyword search
        print("\nTesting keyword search functionality:")
        test_keyword = "test"
        cursor.execute("SELECT * FROM emails WHERE content LIKE ? OR subject LIKE ?", 
                      (f'%{test_keyword}%', f'%{test_keyword}%'))
        results = cursor.fetchall()
        print(f"✓ Search for '{test_keyword}' returned {len(results)} results")
        if results:
            print(f"Sample result: {results[0]}")
        
        conn.close()
    except Exception as e:
        print(f"✗ Database error: {str(e)}")
        traceback.print_exc()
    
    # Test UI server connectivity
    print("\nTesting UI server connectivity:")
    try:
        import requests
        import config
        url = f"http://{config.UI_HOST}:{config.UI_PORT}/api/status"
        print(f"Checking endpoint: {url}")
        response = requests.get(url, timeout=2)
        print(f"✓ UI server responded with status code: {response.status_code}")
        print(f"Response: {response.text[:100]}...")
    except ImportError:
        print("✗ requests module not available. Install with: pip install requests")
    except Exception as e:
        print(f"✗ UI server error: {str(e)}")
    
    # Test processing time measurement
    print("\nTesting processing time measurement:")
    try:
        import time
        import requests
        import config
        
        # Measure actual processing time of a database operation
        start_time = time.time()
        
        # Perform a database operation directly
        import sqlite3
        conn = sqlite3.connect(config.DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emails WHERE rowid IN (SELECT rowid FROM emails ORDER BY RANDOM() LIMIT 10)")
        results = cursor.fetchall()
        conn.close()
        
        actual_duration = time.time() - start_time
        print(f"✓ Direct database query took {actual_duration:.3f} seconds")
        
        # Check UI reported processing time
        try:
            # Try to get processing time from UI API
            url = f"http://{config.UI_HOST}:{config.UI_PORT}/api/metrics"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                metrics = response.json()
                if 'processing_time' in metrics:
                    ui_time = metrics['processing_time']
                    print(f"✓ UI reported processing time: {ui_time}")
                    print(f"  Difference: UI time is {ui_time/actual_duration:.1f}x the actual operation time")
                else:
                    print("✗ UI metrics don't include processing_time")
            else:
                print(f"✗ UI metrics endpoint returned status code: {response.status_code}")
        except Exception as e:
            print(f"✗ Error checking UI metrics: {str(e)}")
            
        # Suggest fix for timing issues
        print("\nPossible fixes for timing issues:")
        print("1. Ensure processing time is measured using start/end timestamps for each operation")
        print("2. Don't use global timer that includes UI idle time")
        print("3. Reset timer between operations")
        print("4. Use a timer decorator for processing functions")
        
        # Code example for proper time measurement
        print("\nExample time measurement code:")
        print("""
def process_operation(operation_data):
    start_time = time.time()
    # Perform actual processing...
    result = do_actual_work(operation_data)
    end_time = time.time()
    processing_time = end_time - start_time
    return {
        'result': result,
        'processing_time': processing_time
    }
        """)
            
    except Exception as e:
        print(f"✗ Processing time test error: {str(e)}")
        traceback.print_exc()
    
    # Continue with existing UI resource checks
    print("\nChecking UI resources:")
    ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
    if os.path.exists(ui_dir):
        template_dir = os.path.join(ui_dir, "templates")
        static_dir = os.path.join(ui_dir, "static")
        
        if os.path.exists(template_dir):
            templates = os.listdir(template_dir)
            print(f"✓ Found {len(templates)} templates: {', '.join(templates[:5])}")
        else:
            print(f"✗ Template directory not found: {template_dir}")
            
        if os.path.exists(static_dir):
            js_files = [f for f in os.listdir(static_dir) if f.endswith('.js')]
            print(f"✓ Found {len(js_files)} JavaScript files: {', '.join(js_files[:5])}")
        else:
            print(f"✗ Static directory not found: {static_dir}")
    else:
        print(f"✗ UI directory not found: {ui_dir}")
    
    print("\n===== UI TEST COMPLETE =====")

def force_run_main(args=None):
    """Force run main.py with captured output."""
    print("\n===== RUNNING MAIN APPLICATION =====")
    
    # Get the absolute path to main.py
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    print(f"Main script: {main_script}")
    
    # Force unbuffered output
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONFAULTHANDLER"] = "1"
    
    cmd_args = [sys.executable, main_script]
    if args:
        cmd_args.extend(args)
    
    print(f"Command: {' '.join(cmd_args)}")
    print("\n--- OUTPUT BEGIN ---\n")
    
    # Run the process with real-time output
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        env=env
    )
    assert process.stdout is not None, "process.stdout should not be None"
    
    # Display output in real-time
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line.rstrip())
            sys.stdout.flush()
    
    # Get exit code
    exit_code = process.poll()
    print("\n--- OUTPUT END ---\n")
    print(f"Process exited with code: {exit_code}")
    
    # Check for error logs
    for log_file in ["/tmp/stone_init_error.log", "/tmp/stone_crash.log"]:
        if os.path.exists(log_file):
            print(f"\nFound error log: {log_file}")
            with open(log_file, 'r') as f:
                print(f.read())
    
    # Try opening UI if needed
    if "--no-ui" not in cmd_args:
        try:
            import config
            url = f"http://{config.UI_HOST}:{config.UI_PORT}"
            print(f"\nAttempting to open UI at {url}")
            webbrowser.open(url)
        except Exception as e:
            print(f"Failed to open UI: {e}")
    
    print("\n===== RUN COMPLETE =====")
    return exit_code

def run_all_diagnostics(args=None):
    """Run all diagnostic tests."""
    print("=" * 60)
    print("STONE EMAIL PROCESSOR - COMPREHENSIVE DIAGNOSTICS")
    print("=" * 60)
    
    test_console_output()
    check_runtime_environment()
    return force_run_main(args)

def main():
    parser = argparse.ArgumentParser(description="Debug tools for Stone Email Processor")
    parser.add_argument("command", choices=["console", "runtime", "run", "all", "ui"],
                       help="Diagnostic command to run")
    parser.add_argument("args", nargs="*", help="Additional arguments to pass to main.py")
    
    if len(sys.argv) < 2:
        parser.print_help()
        return 1
    
    args = parser.parse_args()
    
    if args.command == "console":
        test_console_output()
    elif args.command == "runtime":
        check_runtime_environment()
    elif args.command == "run":
        return force_run_main(args.args)
    elif args.command == "all":
        return run_all_diagnostics(args.args)
    elif args.command == "ui":
        test_ui_functionality()
    
    # Keep terminal open if not a TTY session
    if not sys.stdout.isatty():
        input("\nPress Enter to exit...")
    
    return 0

if __name__ == "__main__":
    # Ensure stdout is unbuffered
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)
    sys.exit(main())