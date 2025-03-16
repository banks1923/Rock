"""
Utilities for identifying and managing email threads/conversations.
"""
import re
import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class ThreadIdentifier:
    """
    Identifies and manages email threads based on headers and content.
    """
    
    # Common prefixes in email subjects
    REPLY_PREFIXES = ['re:', 're :', 'answered:', 'resposta:', 'resp:', 'aw:', 'antwort:']
    FORWARD_PREFIXES = ['fw:', 'fwd:', 'forwarded:', 'weiterleitung:']
    
    # Patterns for email thread identification
    IN_REPLY_TO_HEADER = "In-Reply-To"
    REFERENCES_HEADER = "References"
    THREAD_INDEX_HEADER = "Thread-Index"
    
    def __init__(self):
        """Initialize the thread identifier."""
        self.thread_cache = {}  # message_id -> thread_id
        self.thread_groups = {}  # thread_id -> [message_ids]
    
    @staticmethod
    def normalize_subject(subject: str) -> str:
        """
        Normalize an email subject by removing prefixes and cleaning whitespace.
        
        Args:
            subject: The subject line to normalize
            
        Returns:
            Normalized subject without prefixes like "Re:", "Fwd:", etc.
        """
        if not subject:
            return ""
            
        s = subject.lower().strip()
        
        # Remove all variations of Re:, Fwd:, etc.
        while True:
            original = s
            
            # Remove reply prefixes
            for prefix in ThreadIdentifier.REPLY_PREFIXES + ThreadIdentifier.FORWARD_PREFIXES:
                if s.startswith(prefix):
                    s = s[len(prefix):].strip()
                
            # If no more prefixes found, stop
            if s == original:
                break
                
        # Normalize whitespace
        s = re.sub(r'\s+', ' ', s)
        
        return s.strip()
    
    @staticmethod
    def extract_message_ids(header_value: str) -> List[str]:
        """
        Extract message IDs from a header like References or In-Reply-To.
        
        Args:
            header_value: The value of the header field
            
        Returns:
            List of extracted message IDs
        """
        if not header_value:
            return []
            
        # Extract message IDs enclosed in < >
        return re.findall(r'<([^>]+)>', header_value)
    
    def identify_thread(self, email_data: Dict) -> str:
        """
        Identify which thread an email belongs to based on headers and content.
        
        Args:
            email_data: Dictionary containing email metadata
            
        Returns:
            Thread ID for the email
        """
        message_id = email_data.get('message_id')
        
        # Check if already cached
        if message_id in self.thread_cache:
            return self.thread_cache[message_id]
            
        # First check for explicit thread headers
        related_ids = []
        
        # Check In-Reply-To
        in_reply_to = email_data.get('headers', {}).get(self.IN_REPLY_TO_HEADER, '')
        if in_reply_to:
            related_ids.extend(self.extract_message_ids(in_reply_to))
            
        # Check References
        references = email_data.get('headers', {}).get(self.REFERENCES_HEADER, '')
        if references:
            related_ids.extend(self.extract_message_ids(references))
            
        # Check if any of the related messages is already in a thread
        for related_id in related_ids:
            if related_id in self.thread_cache:
                thread_id = self.thread_cache[related_id]
                self.thread_cache[message_id] = thread_id
                self.thread_groups.setdefault(thread_id, []).append(message_id)
                return thread_id
                
        # If no existing thread found, try subject-based grouping
        subject = email_data.get('subject', '')
        if subject:
            normalized_subject = self.normalize_subject(subject)
            
            # Generate a thread ID from normalized subject
            thread_id = f"thread-{hash(normalized_subject)}"
            
            self.thread_cache[message_id] = thread_id
            self.thread_groups.setdefault(thread_id, []).append(message_id)
            return thread_id
            
        # If all else fails, treat as its own thread
        thread_id = f"thread-{message_id}"
        self.thread_cache[message_id] = thread_id
        self.thread_groups.setdefault(thread_id, []).append(message_id)
        return thread_id
    
    def get_thread_messages(self, thread_id: str) -> List[str]:
        """
        Get all message IDs in a thread.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            List of message IDs in the thread
        """
        return self.thread_groups.get(thread_id, [])
    
    def get_thread_count(self) -> int:
        """
        Get total number of threads identified.
        
        Returns:
            Count of unique threads
        """
        return len(self.thread_groups)
        
    def clear_cache(self):
        """Clear the thread identification cache."""
        self.thread_cache.clear()
        self.thread_groups.clear()

# Helper functions for duplicate content detection

def similarity_score(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings using a simple approach.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity score between 0 and 1
    """
    # Simple implementation - can be replaced with more sophisticated algorithms
    if not text1 or not text2:
        return 0.0
        
    # Convert to sets of words for comparison
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
        
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def are_duplicates(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """
    Determine if two texts are likely duplicates based on similarity.
    
    Args:
        text1: First text string
        text2: Second text string
        threshold: Similarity threshold (0-1) for considering duplicates
        
    Returns:
        True if texts are probable duplicates
    """
    return similarity_score(text1, text2) >= threshold
