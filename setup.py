#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import config
from utils import ensure_data_directory

def setup_project():
    """
    Set up the project directories and initial files.
    """
    print("Setting up Stone Email & Image Processor...")
    
    # Create the data directory
    data_dir = Path(config.MBOX_DIRECTORY)
    ensure_data_directory(data_dir)
    print(f"Data directory created at: {data_dir.absolute()}")
    
    # Create other necessary directories
    for dir_name in ["logs", "temp", "Archive"]:  # Added Archive directory
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"Ensured directory exists: {dir_path}")
    
    # Check for UI Static directory - use existing name format if present
    ui_static_dir = Path("ui_static")
    alt_ui_static_dir = Path("UI Static")
    
    if alt_ui_static_dir.exists():
        ui_static_dir = alt_ui_static_dir
    else:
        ui_static_dir.mkdir(exist_ok=True)
    
    print(f"Ensured UI directory exists: {ui_static_dir}")
    
    # Set up storage directories
    image_storage = data_dir / config.IMAGE_STORAGE_DIR
    pdf_storage = data_dir / config.PDF_STORAGE_DIR
    
    image_storage.mkdir(exist_ok=True)
    pdf_storage.mkdir(exist_ok=True)
    
    print(f"Image storage directory: {image_storage}")
    print(f"PDF storage directory: {pdf_storage}")
    
    # Create OCR cache directory
    ocr_cache = Path("temp") / "ocr_cache"
    ocr_cache.mkdir(exist_ok=True)
    print(f"OCR cache directory: {ocr_cache}")
    
    print("\nSetup complete. To start processing files:")
    print("1. Place your files in the 'data' directory")
    print("2. Run: python main.py")
    print("\nFor more options, run: python main.py --help")
    
    return 0

if __name__ == "__main__":
    sys.exit(setup_project())
