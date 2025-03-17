import os
import logging
import shutil
from pathlib import Path
import config
from typing import Dict, Any, List, Optional
from datetime import datetime

def process_pdf_files(directory_path: str, logger: logging.Logger, metrics: Dict[str, Any]) -> int:
    """
    Process PDF files from the specified directory
    
    Args:
        directory_path: Path to the directory containing PDF files
        logger: Logger instance
        metrics: Dictionary to store processing metrics
        
    Returns:
        int: 0 on success, non-zero on error
    """
    try:
        directory = Path(directory_path)
        pdf_files = list(directory.glob("*.pdf")) + list(directory.glob("*.PDF"))
        
        if not pdf_files:
            logger.info(f"No PDF files found in {directory_path}")
            return 0
            
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        metrics["pdf_files_found"] = len(pdf_files)
        metrics["processed_pdfs"] = 0
        
        # Create PDF storage directory if it doesn't exist
        storage_dir = directory / config.PDF_STORAGE_DIR
        storage_dir.mkdir(exist_ok=True)
        
        # Process each PDF file
        for pdf_path in pdf_files:
            try:
                process_single_pdf(pdf_path, storage_dir, logger)
                metrics["processed_pdfs"] += 1
                
                if metrics["processed_pdfs"] % 10 == 0:
                    logger.info(f"Processed {metrics['processed_pdfs']} PDFs so far")
                    
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path.name}: {e}")
                
        logger.info(f"Successfully processed {metrics['processed_pdfs']} PDF files")
        return 0
        
    except Exception as e:
        logger.exception(f"Error in PDF processing: {e}")
        return 1

def process_single_pdf(pdf_path: Path, storage_dir: Path, logger: logging.Logger) -> None:
    """
    Process a single PDF file
    
    Args:
        pdf_path: Path to the PDF file
        storage_dir: Directory to store processed PDF
        logger: Logger instance
    """
    # Generate a unique filename with timestamp to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"
    destination = storage_dir / new_filename
    
    # Copy the PDF to the storage directory
    shutil.copy2(pdf_path, destination)
    logger.debug(f"Copied {pdf_path.name} to {destination}")
    
    # Here you could add additional processing:
    # - Text extraction using PyPDF2 or pdfplumber
    # - OCR processing for scanned documents
    # - Metadata extraction
    # - Database recording
