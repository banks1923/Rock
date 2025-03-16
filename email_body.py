import email.message
import logging
from typing import Optional, Dict, Any, List, Union, Callable

try:
    import chardet
    from chardet.resultdict import ResultDict
except ImportError:
    chardet = None
    logging.warning("chardet library not found.  Character encoding detection may be less accurate.")

logger = logging.getLogger(__name__)

def decode(payload: Optional[bytes], charset: Optional[str] = None) -> str:
    """
    Decodes binary payload to string with proper character encoding handling.
    
    Args:
        payload: The binary data to decode
        charset: Optional character set to use for decoding
        
    Returns:
        Decoded string, or empty string on failure
    """
    if payload is None:
        return ""
        
    if not isinstance(payload, bytes):
        logger.warning("Payload is not of type bytes; cannot decode")
        return str(payload)
        
    if charset:
        try:
            return payload.decode(charset, errors='replace')
        except LookupError:
            logger.warning(f"Unknown charset {charset}, falling back to detection")
    
    if chardet:
        try:
            result: ResultDict = chardet.detect(payload)
            encoding = result.get('encoding')
            if encoding:
                return payload.decode(encoding, errors='replace')
        except Exception as e:
            logger.warning(f"Character encoding detection failed: {e}")
    
    return payload.decode('utf-8', errors='replace')

def _process_payload(raw_payload: Any, charset: Optional[str], container: List[str]) -> None:
    """
    Helper function to process email payloads consistently.
    
    Args:
        raw_payload: The payload to process
        charset: Character set to use for decoding
        container: List to append decoded content to
    """
    if raw_payload is None:
        return
        
    if isinstance(raw_payload, bytes):
        container.append(decode(raw_payload, charset))
    elif isinstance(raw_payload, list):
        decoded_list = []
        for item in raw_payload:
            if isinstance(item, bytes):
                decoded_list.append(decode(item, charset))
            elif hasattr(item, 'get_payload') and callable(getattr(item, 'get_payload', None)):
                try:
                    binary_item = item.get_payload(decode=True)
                    if isinstance(binary_item, bytes):
                        decoded_list.append(decode(binary_item, charset))
                    else:
                        decoded_list.append(str(binary_item) if binary_item is not None else "")
                except Exception as e:
                    logger.warning(f"Error getting payload from item: {e}")
                    decoded_list.append(str(item) if item is not None else "")
            else:
                decoded_list.append(str(item) if item is not None else "")
        container.append("".join(decoded_list))
    elif isinstance(raw_payload, email.message.Message):
        binary_payload = raw_payload.get_payload(decode=True)
        if isinstance(binary_payload, bytes):
            container.append(decode(binary_payload, charset))
        else:
            container.append(str(binary_payload) if binary_payload is not None else "")
    elif hasattr(raw_payload, 'get_payload') and callable(getattr(raw_payload, 'get_payload', None)):
        try:
            binary_payload = raw_payload.get_payload(decode=True)
            if isinstance(binary_payload, bytes):
                container.append(decode(binary_payload, charset))
            else:
                container.append(str(binary_payload) if binary_payload is not None else "")
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error calling get_payload: {e}")
            container.append(str(raw_payload))
    elif isinstance(raw_payload, (bytes, bytearray, memoryview)):
        container.append(decode(bytes(raw_payload), charset))
    else:
        logger.warning(f"Unexpected payload type: {type(raw_payload)}")
        container.append(str(raw_payload) if raw_payload is not None else "")

def get_email_body(message: email.message.Message) -> str:
    """
    Extracts the plain text body from an email message (handles multipart).
    """
    if message is None:
        logger.error("Received None message object")
        return ""
        
    if not message.is_multipart():
        charset = message.get_content_charset()
        payload = message.get_payload(decode=True)
        if payload is None:
            logger.error("No payload available in the email message.")
            return ""
        
        body_parts = []
        _process_payload(payload, charset, body_parts)
        return "".join(body_parts)
    
    body_parts = []
    html_parts = []
    
    for part in message.walk():
        try:
            content_type = part.get_content_type()
            content_disp = str(part.get("Content-Disposition", ""))
            
            if "attachment" in content_disp:
                continue
                
            if content_type == "text/plain":
                charset = part.get_content_charset()
                raw_payload = part.get_payload(decode=True)
                _process_payload(raw_payload, charset, body_parts)
                    
            elif content_type == "text/html" and not body_parts:
                charset = part.get_content_charset()
                raw_payload = part.get_payload(decode=True)
                _process_payload(raw_payload, charset, html_parts)
                
        except Exception as e:
            logger.error(f"Error processing email part: {e}")
            continue
    
    if body_parts:
        return "".join(body_parts)
    elif html_parts:
        html_content = "".join(html_parts)
        import re
        text = re.sub(r'<[^>]+>', ' ', html_content)
        return re.sub(r'\s+', ' ', text).strip()
    
    return ""