#!/usr/bin/env python3
"""
Extremely simplified script to force terminal output and UI to work.
This bypasses any potential issues with the main script.
"""
import os
import sys
import subprocess
import time

# Direct, unbuffered output
sys.stdout = open(1, 'w', buffering=1, encoding='utf-8', errors='backslashreplace')
print("=" * 60)
print("STONE EMAIL PROCESSOR - FORCE RUN")
print("=" * 60)

# Get the absolute path to main.py
main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
print(f"Main script path: {main_script}")

# Get Python executable
python_exe = sys.executable
print(f"Using Python: {python_exe}")

# Create a very clear marker for output
print("\nRUNNING MAIN APPLICATION NOW:\n" + "=" * 60)

# Force unbuffered output by setting environment variable
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

# Run main.py directly with subprocess, capturing output in real-time
process = subprocess.Popen(
    [python_exe, main_script] + sys.argv[1:],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=1,
    universal_newlines=True,
    env=env
)

# Print output line by line as it happens
while True:
    line = process.stdout.readline()
    if not line and process.poll() is not None:
        break
    if line:
        print(line.rstrip())
        sys.stdout.flush()  # Force flush after every line

# Get exit code
exit_code = process.poll()
print("=" * 60)
print(f"Process exited with code: {exit_code}")

# If the main process didn't open the UI, try opening it manually
print("Attempting to open UI manually...")
try:
    import webbrowser
    webbrowser.open("http://127.0.0.1:8080")
    print("Browser launched")
except Exception as e:
    print(f"Error opening browser: {e}")

print("\nPress Ctrl+C to exit")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting")
