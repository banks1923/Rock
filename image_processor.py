import os
import logging
import shutil
from pathlib import Path
import config
from typing import Dict, Any, List, Optional
from datetime import datetime

def process_image_files(directory_path: str, logger: logging.Logger, metrics: Dict[str, Any]) -> int:
    """
    Process image files (JPEG, PNG) from the specified directory
    
    Args:
        directory_path: Path to the directory containing image files
        logger: Logger instance
        metrics: Dictionary to store processing metrics
        
    Returns:
        int: 0 on success, non-zero on error
    """
    try:
        directory = Path(directory_path)
        image_files = []
        
        # Find all image files
        for ext in config.SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(directory.glob(f"*{ext}"))
            image_files.extend(directory.glob(f"*{ext.upper()}"))
        
        if not image_files:
            logger.info(f"No image files found in {directory_path}")
            return 0
            
        logger.info(f"Found {len(image_files)} image files to process")
        metrics["image_files_found"] = len(image_files)
        metrics["processed_images"] = 0
        
        # Create image storage directory if it doesn't exist
        storage_dir = directory / config.IMAGE_STORAGE_DIR
        storage_dir.mkdir(exist_ok=True)
        
        # Process each image file
        for img_path in image_files:
            try:
                process_single_image(img_path, storage_dir, logger)
                metrics["processed_images"] += 1
                
                if metrics["processed_images"] % 10 == 0:
                    logger.info(f"Processed {metrics['processed_images']} images so far")
                    
            except Exception as e:
                logger.error(f"Error processing image {img_path.name}: {e}")
                
        logger.info(f"Successfully processed {metrics['processed_images']} images")
        return 0
        
    except Exception as e:
        logger.exception(f"Error in image processing: {e}")
        return 1

def process_single_image(image_path: Path, storage_dir: Path, logger: logging.Logger) -> None:
    """
    Process a single image file
    
    Args:
        image_path: Path to the image file
        storage_dir: Directory to store processed image
        logger: Logger instance
    """
    # Generate a unique filename with timestamp to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{image_path.stem}_{timestamp}{image_path.suffix}"
    destination = storage_dir / new_filename
    
    # Copy the image to the storage directory
    shutil.copy2(image_path, destination)
    logger.debug(f"Copied {image_path.name} to {destination}")
    
    # Here you could add additional processing:
    # - Image metadata extraction
    # - Thumbnail generation
    # - OCR processing
    # - Database recording
