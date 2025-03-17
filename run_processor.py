#!/usr/bin/env python3
"""
Simple entry point script to run the processor.
This allows users to simply double-click this file to run the application.
"""
import sys
import os
import subprocess
import webbrowser

def main():
    try:
        print("Starting Stone Email & Image Processor...")
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(script_dir, "main.py")
        
        # Change to the script directory
        os.chdir(script_dir)
        
        # Run the main script
        result = subprocess.run([sys.executable, main_script], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
        
        if result.returncode != 0:
            print("Error running processor:")
            print(result.stderr)
            input("Press Enter to exit...")
            return 1
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
        return 1

if __name__ == "__main__":
    sys.exit(main())
