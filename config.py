import os

# Project Capabilities:
# - Process emails stored in the MBOX_DIRECTORY ("data")
# - Store processed emails in the database file ("emails.db")
# - Filter emails using KEYWORDS (e.g., "urgent", "legal", "contract")
# - Log operations to LOG_FILE ("logs/email_processing.log") at the level LOG_LEVEL ("INFO")
# - Adjust operations for the PACIFIC_TIMEZONE ('America/Los_Angeles')

# Database configuration
DATABASE_FILE = os.environ.get('STONE_DB', '/Users/Shared/stonev2.03/emails.db')

# Temporary directory for file operations
TEMP_DIR = os.environ.get('STONE_TEMP', '/Users/Shared/stonev2.03/temp')

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# OCR Configuration
TESSERACT_PATH = os.environ.get('TESSERACT_PATH', None)  # Path to tesseract if not in PATH
OCR_LANGUAGES = ['eng']  # Languages for OCR
OCR_CACHE_DIR = os.path.join(TEMP_DIR, 'ocr_cache')  # Directory to cache OCR results
os.makedirs(OCR_CACHE_DIR, exist_ok=True)

# File export options
ALLOWED_EXPORT_FORMATS = ['txt', 'csv', 'json', 'html']

# Maximum size of file uploads (5MB)
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

# Input directory settings - this is where you place files for processing
MBOX_DIRECTORY = "data"  # Default directory for all input files (emails, images, PDFs)

# Define supported file extensions for different types
SUPPORTED_EXTENSIONS = {
    'email': ['.mbox', '.MBOX', '.eml', '.EML', ''],  # Empty string allows for files named 'mbox' without extension
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
    'document': ['.pdf', '.PDF']
}

KEYWORDS = ["urgent", "legal", "contract"]
LOG_FILE = "logs/email_processing.log"
LOG_LEVEL = "INFO"
PACIFIC_TIMEZONE = 'America/Los_Angeles'
VERSION = "2.0.3"  # Added version number

# Image processing settings
IMAGE_PROCESSING_ENABLED = True
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
IMAGE_STORAGE_DIR = "processed_images"  # Subdirectory to store processed images

# Document processing settings
DOCUMENT_PROCESSING_ENABLED = True  # Enable processing of PDF documents
PDF_STORAGE_DIR = "processed_documents"  # Subdirectory to store processed documents

# UI settings
AUTO_OPEN_UI = True  # Whether to automatically open the UI when processing completes
UI_PORT = 8080  # Port for the web UI
UI_HOST = "127.0.0.1"  # Host for the web UI (localhost)
BROWSER_PATH = None  # Set to specific path if auto-detection fails