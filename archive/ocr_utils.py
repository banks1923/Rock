"""
Utilities for performing OCR on email attachments
"""
import os
import io
import tempfile
import logging
import mimetypes
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
import pytesseract
import pdf2image
import config

# Set up logging
logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    Process attachments through OCR to extract text content
    """
    
    # Supported MIME types for OCR processing
    SUPPORTED_IMAGE_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/tiff',
        'image/bmp', 'image/x-ms-bmp'
    ]
    
    SUPPORTED_PDF_TYPES = [
        'application/pdf'
    ]
    
    def __init__(self, tesseract_path: Optional[str] = None, language: str = 'eng'):
        """
        Initialize OCR processor with optional custom tesseract path.
        
        Args:
            tesseract_path: Path to tesseract executable (if not in PATH)
            language: Language for OCR (default: English)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        self.language = language
        
    def _process_image(self, image: Image.Image) -> str:
        """
        Process a PIL Image through OCR.
        
        Args:
            image: PIL Image object to process
            
        Returns:
            Extracted text string
        """
        try:
            return pytesseract.image_to_string(image, lang=self.language)
        except Exception as e:
            logger.error(f"OCR error processing image: {e}")
            return ""
    
    def process_image_file(self, file_path: str) -> str:
        """
        Process an image file through OCR.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Extracted text string
        """
        try:
            with Image.open(file_path) as img:
                return self._process_image(img)
        except Exception as e:
            logger.error(f"Error opening image {file_path}: {e}")
            return ""
    
    def process_image_bytes(self, image_data: bytes, mime_type: str) -> str:
        """
        Process image data through OCR.
        
        Args:
            image_data: Binary image data
            mime_type: MIME type of the image
            
        Returns:
            Extracted text string
        """
        if mime_type not in self.SUPPORTED_IMAGE_TYPES:
            logger.warning(f"Unsupported image type: {mime_type}")
            return ""
            
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return self._process_image(img)
        except Exception as e:
            logger.error(f"Error processing image bytes: {e}")
            return ""
    
    def process_pdf_bytes(self, pdf_data: bytes) -> str:
        """
        Process PDF data through OCR.
        
        Args:
            pdf_data: Binary PDF data
            
        Returns:
            Extracted text string
        """
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(pdf_data)
                temp_pdf_path = temp_pdf.name
            
            # Convert PDF to images
            try:
                pages = pdf2image.convert_from_path(temp_pdf_path)
            except Exception as e:
                logger.error(f"Error converting PDF to images: {e}")
                return ""
            
            # Process each page through OCR
            text_parts = []
            for i, page in enumerate(pages):
                logger.debug(f"Processing PDF page {i+1}/{len(pages)}")
                text = self._process_image(page)
                if text.strip():
                    text_parts.append(text)
            
            # Combine texts with page markers
            full_text = "\n\n--- Page Break ---\n\n".join(text_parts)
            return full_text
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return ""
        finally:
            # Clean up the temporary file
            if 'temp_pdf_path' in locals():
                try:
                    os.unlink(temp_pdf_path)
                except:
                    pass
    
    def process_attachment(self, attachment_data: bytes, mime_type: str, 
                          filename: str) -> Optional[str]:
        """
        Process an attachment through OCR based on its type.
        
        Args:
            attachment_data: Binary attachment data
            mime_type: MIME type of the attachment
            filename: Original filename of the attachment
            
        Returns:
            Extracted text or None if not suitable for OCR
        """
        # If mime_type is not provided, try to guess from filename
        if not mime_type:
            guessed_mime_type, _ = mimetypes.guess_type(filename)
            if guessed_mime_type:
                mime_type = guessed_mime_type
            
        if mime_type is None:
            return None
            
        # Process based on MIME type
        if mime_type in self.SUPPORTED_IMAGE_TYPES:
            return self.process_image_bytes(attachment_data, mime_type)
        elif mime_type in self.SUPPORTED_PDF_TYPES:
            return self.process_pdf_bytes(attachment_data)
        else:
            logger.debug(f"Unsupported MIME type for OCR: {mime_type}")
            return None

# Create a singleton instance of the OCR processor
ocr_processor = OCRProcessor(tesseract_path=config.TESSERACT_PATH if hasattr(config, 'TESSERACT_PATH') else None)

def process_attachment_ocr(attachment_data: bytes, mime_type: str, filename: str) -> Optional[str]:
    """
    Process an attachment through OCR.
    
    Args:
        attachment_data: Binary attachment data
        mime_type: MIME type of the attachment
        filename: Original filename of the attachment
        
    Returns:
        Extracted text or None if not suitable for OCR
    """
    return ocr_processor.process_attachment(attachment_data, mime_type, filename)
