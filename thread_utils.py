"""
Utilities for identifying and managing email threads.
"""

import re
import logging
from typing import Dict, Any, Optional, Set, List
import hashlib

logger = logging.getLogger(__name__)

class ThreadIdentifier:
    """
    Identifies and manages email threads by analyzing message headers and content.
    """
    
    def __init__(self):
        """Initialize the thread identifier with an empty threads dictionary."""
        self.threads = {}
        self.subject_threads = {}
        self.reference_map = {}
        self.next_thread_id = 1
        self._normalized_cache = {}  # Cache for normalized subjects
        
    def get_thread_count(self) -> int:
        """Return the number of unique threads identified."""
        return len(self.threads)
        
    def identify_thread(self, email: Dict[str, Any]) -> Optional[str]:
        """
        Identify which thread an email belongs to based on headers and content.
        
        Args:
            email: Dictionary containing email data
            
        Returns:
            Thread identifier string or None if no thread could be identified
        """
        if not email:
            return None
            
        message_id = email.get('message_id')
        if not message_id:
            return None
            
        # Check if this message is already in a thread
        if message_id in self.reference_map:
            return self.reference_map[message_id]
            
        # Look for references and in-reply-to in the raw email
        references = self._extract_references(email)
        
        if references:
            # Check if any reference is already in a thread
            for ref in references:
                if ref in self.reference_map:
                    thread_id = self.reference_map[ref]
                    # Add this message to the same thread
                    self.reference_map[message_id] = thread_id
                    return thread_id
            
            # No existing thread found, create a new one
            thread_id = f"thread-{self.next_thread_id}"
            self.next_thread_id += 1
            
            # Register all references and this message in the new thread
            self.threads[thread_id] = set(references)
            self.threads[thread_id].add(message_id)
            
            for ref in references:
                self.reference_map[ref] = thread_id
            self.reference_map[message_id] = thread_id
            
            return thread_id
            
        # Try subject-based threading as a fallback
        subject = email.get('subject', '')
        if subject:
            # Normalize subject by removing Re:, Fwd:, etc.
            normalized_subject = self._normalize_subject(subject)
            if normalized_subject:
                if normalized_subject in self.subject_threads:
                    thread_id = self.subject_threads[normalized_subject]
                    self.reference_map[message_id] = thread_id
                    return thread_id
                else:
                    # Create a new subject-based thread
                    thread_id = f"subject-{self.next_thread_id}"
                    self.next_thread_id += 1
                    self.subject_threads[normalized_subject] = thread_id
                    self.reference_map[message_id] = thread_id
                    return thread_id
        
        # Create a singleton thread for this message
        thread_id = f"singleton-{message_id[-8:]}" if len(message_id) > 8 else f"singleton-{self.next_thread_id}"
        self.next_thread_id += 1
        self.reference_map[message_id] = thread_id
        return thread_id

    def _extract_references(self, email: Dict[str, Any]) -> Set[str]:
        """
        Extract message references from email data.
        
        Args:
            email: Dictionary containing email data
            
        Returns:
            Set of referenced message IDs
        """
        references = set()
        
        # Add the current message ID
        message_id = email.get('message_id')
        if message_id:
            references.add(message_id)
        
        # Extract from content if available
        content = email.get('content', '')
        if content:
            # Look for message IDs in the content (basic pattern)
            message_id_pattern = r'<[^<>@\s]+@[^<>\s]+>'
            for match in re.finditer(message_id_pattern, content):
                references.add(match.group(0))
                
        return references
        
    def _normalize_subject(self, subject: str) -> str:
        """
        Normalize email subject by removing prefixes like Re:, Fwd:, etc.
        
        Args:
            subject: Original email subject
            
        Returns:
            Normalized subject string
        """
        if not subject:
            return ""
        if subject in self._normalized_cache:
            return self._normalized_cache[subject]
            
        # Remove common prefixes
        prefixes = [
            r'^re:\s*', 
            r'^fwd:\s*', 
            r'^fw:\s*', 
            r'^reply:\s*',
            r'^\[\w+\]\s*'  # [Tag] pattern
        ]
        
        normalized = subject.lower()
        
        for pattern in prefixes:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
            
        normalized = normalized.strip()
        self._normalized_cache[subject] = normalized
        return normalized
