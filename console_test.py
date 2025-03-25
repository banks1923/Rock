#!/usr/bin/env python3
"""
Simple test script to verify console output methods.
This bypasses all application logic to focus solely on output capability.
"""
import sys
import os
import time

def test_output_methods():
    """Test various output methods to see which ones work."""
    print("\n===== CONSOLE OUTPUT TEST =====")
    print("Method 1: print() function")
    print("If you see this, print() works")
    
    time.sleep(0.5)  # Short delay between tests
    
    print("\nMethod 2: sys.stdout.write()")
    sys.stdout.write("If you see this, sys.stdout.write() works\n")
    sys.stdout.flush()
    
    time.sleep(0.5)
    
    print("\nMethod 3: sys.stderr.write()")
    sys.stderr.write("If you see this, sys.stderr.write() works\n")
    sys.stderr.flush()
    
    time.sleep(0.5)
    
    print("\nMethod 4: os.system echo")
    os.system('echo "If you see this, os.system echo works"')
    
    print("\n===== TEST COMPLETE =====")
    print("If you don't see all test messages, there might be output redirection or")
    print("buffering issues in your environment.")

if __name__ == "__main__":
    # Run the test
    test_output_methods()
    
    # Keep terminal open if run by double-clicking
    if sys.stdout.isatty():
        input("\nPress Enter to exit...")
