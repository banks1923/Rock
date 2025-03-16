import email.utils
import pytz
from datetime import datetime
import logging
from exceptions import EmailParsingError
from email_body import get_email_body
import config

logger = logging.getLogger(__name__)

def parse_email(message):
    """
    Consolidates extraction of email headers and body into a unified function.
    """
    try:
        message_id = message.get("Message-ID", "") or message.get("Message-Id", "")
        if not message_id:
            message_id = f"generated-{hash(message.as_string())}"
            
        sender = message.get("From", "").strip()
        receiver = message.get("To", "").strip()
        subject = message.get("Subject", "").strip()
        date_str = message.get("Date", "").strip()
        
        date_parsed = None
        if date_str:
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                if dt:
                    if not dt.tzinfo:
                        dt = pytz.utc.localize(dt)
                    target_tz = pytz.timezone(config.PACIFIC_TIMEZONE)
                    date_parsed = dt.astimezone(target_tz)
                else:
                    logger.warning(f"Could not parse date string: {date_str}")
            except Exception as e:
                logger.warning(f"Error parsing date: {date_str}: {e}")
        
        content = get_email_body(message)
        
        return {
            "message_id": message_id,
            "content": content,
            "sender": sender,
            "date": date_parsed,
            "subject": subject,
            "receiver": receiver,
        }
    except Exception as e:
        logger.exception(f"Error processing email: {e}")
        raise EmailParsingError(f"Error processing email: {e}") from e