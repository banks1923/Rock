# Project Capabilities:
# - Process emails stored in the MBOX_DIRECTORY ("data")
# - Store processed emails in the database file ("emails.db")
# - Filter emails using KEYWORDS (e.g., "urgent", "legal", "contract")
# - Log operations to LOG_FILE ("logs/email_processing.log") at the level LOG_LEVEL ("INFO")
# - Adjust operations for the PACIFIC_TIMEZONE ('America/Los_Angeles')

DATABASE_FILE = "emails.db"
MBOX_DIRECTORY = "data"
KEYWORDS = ["urgent", "legal", "contract"]
LOG_FILE = "logs/email_processing.log"
LOG_LEVEL = "INFO"
PACIFIC_TIMEZONE = 'America/Los_Angeles'
VERSION = "2.0.3"  # Added version number