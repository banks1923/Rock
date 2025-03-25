#!/usr/bin/env python3
"""
Diagnostic script to verify console output functionality and detect potential issues.
Run this script standalone to test basic output capabilities.
"""
import sys
import os
import io
import logging
import traceback
import importlib

# Basic output tests
print("=== BASIC OUTPUT TEST ===")
print("Standard output test (stdout)")
sys.stdout.write("Direct stdout write test\n")
sys.stdout.flush()

print("Standard error test (stderr)", file=sys.stderr)
sys.stderr.write("Direct stderr write test\n")
sys.stderr.flush()

# Identify Python environment
print("\n=== PYTHON ENVIRONMENT ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"sys.path: {sys.path}")

# Test stdout/stderr redirection
print("\n=== STDOUT/STDERR STATUS ===")
print(f"sys.stdout type: {type(sys.stdout)}")
print(f"sys.stderr type: {type(sys.stderr)}")
print(f"sys.stdout is a tty: {sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else 'N/A'}")
print(f"sys.stderr is a tty: {sys.stderr.isatty() if hasattr(sys.stderr, 'isatty') else 'N/A'}")

# Test basic logging
print("\n=== LOGGING TEST ===")
test_logger = logging.getLogger("test_logger")
test_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
test_logger.addHandler(handler)
test_logger.info("This is a test log message")

# Test import of main components
print("\n=== IMPORTING KEY MODULES ===")
modules_to_test = ['config', 'utils', 'database', 'email_processor', 'ui_manager']
import_results = {}

for module_name in modules_to_test:
    try:
        module = importlib.import_module(module_name)
        import_results[module_name] = "Success"
    except Exception as e:
        import_results[module_name] = f"Error: {str(e)}"
        print(f"Failed to import {module_name}: {e}")

for module_name, result in import_results.items():
    print(f"{module_name}: {result}")

# Test file access
print("\n=== FILE ACCESS TEST ===")
try:
    with open("test_output.txt", "w") as f:
        f.write("Test file write")
    print("Successfully wrote to test file")
    os.remove("test_output.txt")
    print("Successfully deleted test file")
except Exception as e:
    print(f"File access error: {e}")

# Look for stdout/stderr redirect in config
print("\n=== CONFIG CHECK ===")
try:
    import config
    print(f"Log file from config: {config.LOG_FILE}")
    
    # Check for any stdout/stderr redirection in config
    config_vars = vars(config)
    for name, value in config_vars.items():
        if "stdout" in name.lower() or "stderr" in name.lower() or "redirect" in name.lower():
            print(f"Potential output redirection in config: {name}={value}")
except Exception as e:
    print(f"Error checking config: {e}")

if __name__ == "__main__":
    print("\n=== DIAGNOSTIC COMPLETE ===")
    print("If you see this message in your terminal, basic output is working")
    print("Please run the script with elevated verbosity using:")
    print("python debug_runtime.py | tee debug_output.txt")
