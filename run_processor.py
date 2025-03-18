#!/usr/bin/env python3
"""
Simple entry point script to run the processor.
This allows users to simply double-click this file to run the application.
"""
import sys
import os
import subprocess
import traceback
import webbrowser
import time

def main():
    try:
        print("Starting Stone Email & Image Processor...")
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(script_dir, "main.py")
        
        # Verify main.py exists
        if not os.path.exists(main_script):
            print(f"Error: Could not find {main_script}")
            input("Press Enter to exit...")
            return 1
            
        # Change to the script directory
        os.chdir(script_dir)
        print(f"Working directory: {script_dir}")
        
        # Check if all required modules are available
        required_modules = ["logging", "threading", "sqlite3", "email", "pathlib"]
        for module in required_modules:
            try:
                __import__(module)
                print(f"✓ {module} module available")
            except ImportError:
                print(f"✗ {module} module missing!")
                
        # Check Python version
        print(f"Python version: {sys.version}")
        
        # Run the main script with output shown
        print("\nStarting application...\n" + "-"*50)
        
        # Using current Python interpreter to run the script
        result = subprocess.run([sys.executable, main_script], 
                               stdout=sys.stdout,  # Show output directly
                               stderr=sys.stdout,  # Show errors directly
                               universal_newlines=True)
        
        if result.returncode != 0:
            print("\n" + "-"*50)
            print(f"Application exited with error code: {result.returncode}")
            input("Press Enter to exit...")
            return 1
        
        return 0
    except Exception as e:
        print("\n" + "-"*50)
        print(f"Error running application: {e}")
        print("\nDetailed error information:")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return 1

if __name__ == "__main__":
    sys.exit(main())
