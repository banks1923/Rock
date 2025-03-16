<<<<<<< HEAD
import os

=======
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
# Project Capabilities:
# - Process emails stored in the MBOX_DIRECTORY ("data")
# - Store processed emails in the database file ("emails.db")
# - Filter emails using KEYWORDS (e.g., "urgent", "legal", "contract")
# - Log operations to LOG_FILE ("logs/email_processing.log") at the level LOG_LEVEL ("INFO")
# - Adjust operations for the PACIFIC_TIMEZONE ('America/Los_Angeles')

<<<<<<< HEAD
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

=======
DATABASE_FILE = "emails.db"
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
MBOX_DIRECTORY = "data"
KEYWORDS = ["urgent", "legal", "contract"]
LOG_FILE = "logs/email_processing.log"
LOG_LEVEL = "INFO"
PACIFIC_TIMEZONE = 'America/Los_Angeles'
VERSION = "2.0.3"  # Added version number