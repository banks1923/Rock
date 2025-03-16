"""
Text processing utilities for the Stone Email System.
"""

import re
import html
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('text_utils')

class TextCleaner:
    """
    Class for cleaning and formatting text content from emails.
    Provides various methods for text normalization and enhancement.
    """
    
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        """
        Initialize the text cleaner with options.
        
        Args:
            options: Configuration options for text processing
        """
        self.default_options = {
            'strip_html': True,
            'use_beautiful_soup': True,  # More robust HTML parsing
            'normalize_whitespace': True,
            'handle_urls': True,
            'format_quotes': True,
            'remove_signatures': True,
            'detect_encodings': True,
            'max_length': 10000,
            'preserve_emoji': False,
            'highlight_keywords': [],
            'extract_header_info': True,
            'format_sender_changes': True,  # New option for sender change detection
            'sender_change_separator': '\n---\n',  # Separator to use when sender changes
        }
        
        self.options = self.default_options.copy()
        if options:
            self.options.update(options)
    
    def clean(self, text: str) -> str:
        """
        Apply all enabled cleaning operations to text.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if text is None:
            return "(No content)"
            
        cleaned = text
        
        # Detect and fix encoding issues
        if self.options.get('detect_encodings'):
            cleaned = self._fix_encoding(cleaned)
            
        # Strip HTML tags
        if self.options.get('strip_html'):
            if self.options.get('use_beautiful_soup'):
                try:
                    soup = BeautifulSoup(cleaned, 'html.parser')
                    cleaned = soup.get_text(separator=' ', strip=True)
                except Exception:
                    # Fall back to regex if BeautifulSoup fails
                    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
            else:
                cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
                
            cleaned = html.unescape(cleaned)
        
        # Extract header info if present in the body
        if self.options.get('extract_header_info'):
            cleaned = self._extract_headers(cleaned)
            
        # Normalize whitespace
        if self.options.get('normalize_whitespace'):
            cleaned = self._normalize_whitespace(cleaned)
        
        # Format URLs
        if self.options.get('handle_urls'):
            cleaned = self._format_urls(cleaned)
        
        # Format quoted content
        if self.options.get('format_quotes'):
            cleaned = self._format_quotes(cleaned)
        
        # Remove signatures
        if self.options.get('remove_signatures'):
            cleaned = self._remove_signatures(cleaned)
        
        # Highlight keywords
        if self.options.get('highlight_keywords') and len(self.options.get('highlight_keywords', [])) > 0:
            cleaned = self._highlight_keywords(cleaned)
        
        # Format sender changes in conversation threads
        if self.options.get('format_sender_changes'):
            cleaned = self._format_sender_changes(cleaned)
        
        # Truncate long content
        max_length = self.options.get('max_length', 0)
        if max_length > 0 and len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "... [truncated]"
        
        return cleaned.strip()
    
    def _fix_encoding(self, text: str) -> str:
        """Fix common encoding issues in text"""
        # Handle common encoding problems
        replacements = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€¦': '...',
            'â€"': '-',
            'â€"': '-',
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã¢': 'â',
            'Ã': 'à',
        }
        
        for bad, good in replacements.items():
            text = text.replace(bad, good)
            
        return text
    
    def _extract_headers(self, text: str) -> str:
        """Extract and format email headers found in the body"""
        # Look for common email header patterns and format them
        header_pattern = r'^(From|To|Cc|Bcc|Date|Subject|Sent): (.*?)$'
        lines = text.split('\n')
        formatted_lines = []
        in_header_block = False
        header_block_lines = []
        
        for line in lines:
            header_match = re.match(header_pattern, line, re.IGNORECASE)
            if header_match:
                if not in_header_block:
                    in_header_block = True
                header_block_lines.append(line)
            else:
                if in_header_block and not line.strip():
                    # Continuing header block with an empty line
                    header_block_lines.append(line)
                else:
                    if in_header_block:
                        # End of header block
                        if header_block_lines:
                            # Process and format headers
                            formatted_lines.append("--- Forwarded Headers ---")
                            formatted_lines.extend(header_block_lines)
                            formatted_lines.append("--- End Headers ---")
                            header_block_lines = []
                        in_header_block = False
                    formatted_lines.append(line)
        
        # Handle case where headers are at end of text
        if in_header_block and header_block_lines:
            formatted_lines.append("--- Forwarded Headers ---")
            formatted_lines.extend(header_block_lines)
            formatted_lines.append("--- End Headers ---")
        
        return '\n'.join(formatted_lines)
        
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Fix newlines - preserve paragraph breaks but remove excessive empty lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
    
    def _format_urls(self, text: str) -> str:
        """Format URLs in text for better visibility"""
        url_pattern = r'(https?://[^\s]+)'
        return re.sub(url_pattern, r'<link>\1</link>', text)
    
    def _format_quotes(self, text: str) -> str:
        """Format quoted email content"""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip().startswith('>'):
                formatted_lines.append(f"<i>{line}</i>")
            else:
                formatted_lines.append(line)
                
        return '\n'.join(formatted_lines)
    
    def _remove_signatures(self, text: str) -> str:
        """Remove common email signature patterns"""
        signature_patterns = [
            r'--\s*\n.*',  # Standard signature delimiter
            r'Sent from .*',  # Mobile signatures
            r'Get Outlook for .*',  # Outlook signatures
            r'___+.*',  # Underline-style signatures
        ]
        
        result = text
        for pattern in signature_patterns:
            result = re.sub(pattern, '', result, flags=re.DOTALL)
            
        return result
    
    def _highlight_keywords(self, text: str) -> str:
        """Highlight specified keywords in text"""
        result = text
        for keyword in self.options.get('highlight_keywords', []):
            if keyword.strip():
                pattern = re.compile(re.escape(keyword.strip()), re.IGNORECASE)
                result = pattern.sub(f"<b>{keyword}</b>", result)
                
        return result
    
    def _format_sender_changes(self, text: str) -> str:
        """
        Detect and format changes in sender within conversation threads.
        
        Looks for common messaging patterns indicating different senders
        and adds formatting to make the conversation more readable.
        
        Args:
            text: Text to process
            
        Returns:
            Text with formatting at sender change points
        """
        try:
            # Common patterns indicating a sender in conversations
            sender_patterns = [
                # Standard email reply format
                r'^On .+ wrote:$',
                # Common chat patterns
                r'^([A-Za-z0-9._-]+):',  # username:
                r'^\[(.*?)\]:',  # [username]:
                r'^<([^>]+)>:?',  # <username>:
                # Time-prefixed messages
                r'^\[\d{1,2}:\d{2}(?: [AP]M)?\] (.+?):',  # [10:30 AM] Username:
                # Special format in some platforms
                r'^From: (.+?) \(\d{1,2}/\d{1,2}/\d{2,4}\):',  # From: User (12/25/2023):
            ]
            
            lines = text.split('\n')
            processed_lines = []
            current_sender = None
            
            for i, line in enumerate(lines):
                sender_detected = False
                
                # Check if this line indicates a sender change
                for pattern in sender_patterns:
                    match = re.match(pattern, line.strip(), re.IGNORECASE)
                    if match:
                        # Fixed: Safely extract group if it exists
                        new_sender = None
                        if match and match.groups():
                            new_sender = match.group(1)
                        else:
                            new_sender = "Unknown"
                            
                        if current_sender and new_sender != current_sender:
                            separator = self.options.get('sender_change_separator', '\n---\n')
                            processed_lines.append(separator)
                        current_sender = new_sender
                        sender_detected = True
                        break
                
                # For lines not matching sender patterns, check for indirect indicators
                if not sender_detected:
                    # Look for conversation separators (e.g., "----Original Message----")
                    msg_separator_patterns = [
                        r'^-{3,} ?Original Message ?-{3,}$',
                        r'^={3,}$',
                        r'^_{3,}$',
                        r'^From: .+$',  # From: lines without dates
                        r'^Sent: .+$',  # Sent: lines
                    ]
                    
                    for pattern in msg_separator_patterns:
                        if re.match(pattern, line.strip()):
                            if current_sender:
                                separator = self.options.get('sender_change_separator', '\n---\n')
                                processed_lines.append(separator)
                                current_sender = None  # Reset current sender
                                break
                
                # Add the line to our processed output
                processed_lines.append(line)
            
            result = '\n'.join(processed_lines)
            logger.debug(f"Sender change detection processed {len(lines)} lines, resulting in {len(processed_lines)} lines")
            return result
            
        except Exception as e:
            logger.error(f"Error in _format_sender_changes: {e}")
            # Return original text if there's an error
            return text

def get_cleaner(options=None):
    """
    Factory function to create a text cleaner with given options.
    
    Args:
        options: Cleaning configuration options
        
    Returns:
        Configured TextCleaner instance
    """
    return TextCleaner(options)
