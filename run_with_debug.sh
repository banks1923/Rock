#!/bin/bash
# Debug wrapper script to run the application with output capture

# Make script executable
chmod +x $0

# Set debug flags
export PYTHONUNBUFFERED=1
export PYTHONFAULTHANDLER=1

# Determine the Python executable to use
PYTHON_EXEC="${VIRTUAL_ENV:-/Users/Shared/stonev2.03/.venv}/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC=$(which python3)
fi

echo "Using Python: $PYTHON_EXEC"
echo "Working directory: $(pwd)"
echo "Running main.py with output capture..."

# Run the program and capture both stdout and stderr
$PYTHON_EXEC /Users/Shared/stonev2.03/main.py "$@" 2>&1 | tee /tmp/stone_output.log

# Check for error logs
if [ -f "/tmp/stone_init_error.log" ]; then
    echo "ERROR DETECTED! See /tmp/stone_init_error.log for details"
    cat /tmp/stone_init_error.log
fi

if [ -f "/tmp/stone_crash.log" ]; then
    echo "CRASH DETECTED! See /tmp/stone_crash.log for details"
    cat /tmp/stone_crash.log
fi

echo "Execution complete. Debug log available at /tmp/stone_output.log"
