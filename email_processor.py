import os
import logging
import mailbox
import time
import sys
from typing import List, Dict, Optional, Any, Iterator, Generator
from pathlib import Path

# Make sure thread_utils can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try different import approaches to handle potential issues
try:
    from email_parser import parse_email
    from exceptions import EmailParsingError
    from database import insert_email_data, update_thread_info
    import config
    from utils import get_file_hash, check_memory_usage
    
    # Try to import ThreadIdentifier, fallback to a simple implementation if not available
    try:
        from thread_utils import ThreadIdentifier
    except ImportError:
        # Simple fallback implementation
        class ThreadIdentifier:
            def __init__(self):
                self.threads = {}
                self.next_id = 1
                
            def get_thread_count(self):
                return len(self.threads)
                
            def identify_thread(self, email):
                if not email or 'message_id' not in email:
                    return None
                message_id = email['message_id']
                if message_id in self.threads:
                    return self.threads[message_id]
                thread_id = f"thread-{self.next_id}"
                self.next_id += 1
                self.threads[message_id] = thread_id
                return thread_id
                
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

def process_mbox_files(directory: str, logger=None, dry_run: bool = False, 
                      batch_size: int = 100, file_cache: Optional[Dict] = None,
                      max_memory_pct: int = 80, metrics: Optional[Dict] = None,
                      use_threading: bool = True) -> int:
    """
    Process all .mbox files in the given directory.
    
    Args:
        directory: Directory path containing the .mbox files
        logger: Logger instance
        dry_run: If True, don't modify the database
        batch_size: Number of emails to process in each batch
        file_cache: Cache of previously processed files
        max_memory_pct: Maximum memory usage percentage
        metrics: Dictionary to update with processing metrics
        use_threading: Whether to identify and group emails by thread
        
    Returns:
        int: 0 on success, non-zero on error
    """
    if metrics is None:
        metrics = {"processed_files": 0, "processed_emails": 0, "start_time": time.time()}
        
    if logger is None:
        logger = logging.getLogger(__name__)
    
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error(f"Directory does not exist: {directory}")
        return 1
        
    # Use Path.glob for efficient directory listing with pattern matching
    mbox_files = list(dir_path.glob('*.mbox'))
    if not mbox_files:
        logger.warning(f"No .mbox files found in directory: {directory}")
        return 0
        
    logger.info(f"Found {len(mbox_files)} .mbox files to process")
    
    # Initialize thread identifier if threading is enabled
    thread_identifier = ThreadIdentifier() if use_threading else None
    thread_stats = {"thread_count": 0, "emails_grouped": 0} if use_threading else None
    
    # Process each file
    for mbox_path in mbox_files:
        mbox_file = str(mbox_path)
        logger.info(f"Processing file: {mbox_file}")
        
        # Skip unchanged files if requested
        if file_cache is not None:
            try:
                current_hash = get_file_hash(mbox_file)
                if mbox_file in file_cache and file_cache[mbox_file] == current_hash:
                    logger.info(f"Skipping unchanged file: {mbox_file}")
                    metrics["processed_files"] += 1  # Count as processed even if skipped
                    continue
                else:
                    # Update cache with current hash
                    file_cache[mbox_file] = current_hash
            except Exception as e:
                logger.warning(f"Error calculating file hash for {mbox_file}: {e}")
        
        # Check memory usage before processing each file
        if not check_memory_usage(max_memory_pct, logger):
            logger.warning("Memory usage too high, pausing processing")
            return 2

        try:
            # Process the file in batches for better memory management
            batch_metrics = {"total_emails": 0, "processed_emails": 0}
            
            # First, count the total emails in the mbox
            mb = None
            try:
                mb = mailbox.mbox(mbox_file)
                batch_metrics["total_emails"] = len(mb)
            finally:
                if mb is not None:
                    mb.close()
            
            # Then process in batches
            for batch in process_mbox_batches(mbox_file, batch_size, logger, batch_metrics):
                # Group emails by thread if threading is enabled
                if use_threading and not dry_run:
                    thread_groups = {}
                    
                    for email in batch:
                        if thread_identifier:  # Check that thread_identifier exists
                            thread_id = thread_identifier.identify_thread(email)
                            if thread_id:
                                thread_groups.setdefault(thread_id, []).append(email)
                                # Add thread_id to each email
                                email['thread_id'] = thread_id
                    
                    # Update thread stats
                    if thread_identifier and thread_stats:
                        thread_stats["thread_count"] = thread_identifier.get_thread_count()
                        thread_stats["emails_grouped"] += len(batch)
                
                if not dry_run:
                    try:
                        inserted = insert_email_data(batch, config.DATABASE_FILE, batch_size)
                        logger.info(f"Inserted {inserted} emails from batch")
                        metrics["processed_emails"] += inserted
                        batch_metrics["processed_emails"] += inserted
                        
                        # Update thread information in the database
                        if use_threading and thread_groups:
                            for thread_id, thread_emails in thread_groups.items():
                                try:
                                    update_thread_info(thread_id, thread_emails, config.DATABASE_FILE)
                                except Exception as e:
                                    logger.error(f"Error updating thread info for {thread_id}: {e}")
                    except Exception as e:
                        logger.exception(f"Error inserting batch from {mbox_file}: {e}")
                else:
                    # In dry run mode, just count the emails
                    logger.info(f"Dry run: would have inserted {len(batch)} emails from batch")
                    metrics["processed_emails"] += len(batch)
                    batch_metrics["processed_emails"] += len(batch)
                
                # Check memory after each batch
                if not check_memory_usage(max_memory_pct, logger):
                    logger.warning("Memory usage too high after batch, pausing processing")
                    return 2
            
            metrics["processed_files"] += 1
            logger.info(f"Completed processing {mbox_file}: {batch_metrics['processed_emails']} of {batch_metrics['total_emails']} emails processed")
                
        except Exception as e:
            logger.exception(f"Error processing mbox file {mbox_file}: {e}")
            return 1
            
    # Add thread stats to metrics if available
    if thread_stats and metrics:
        metrics.update(thread_stats)
    
    return 0

def process_mbox_batches(mbox_file: str, batch_size: int, logger, metrics: Dict = None) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Generator that processes an mbox file in batches to control memory usage.
    
    Args:
        mbox_file: Path to the mbox file
        batch_size: Number of emails to process in each batch
        logger: Logger instance
        metrics: Dictionary to track processing metrics
    
    Yields:
        Batches of processed emails as lists of dictionaries
    """
    logger.info(f"Processing mbox file in batches: {mbox_file}")
    
    mbox = None
    try:
        mbox = mailbox.mbox(mbox_file)
        
        # Process in batches
        current_batch = []
        total_processed = 0
        
        # Get the total count for progress reporting
        total_messages = len(mbox)
        if metrics is not None:
            metrics["total_emails"] = total_messages
        logger.info(f"Found {total_messages} messages in {mbox_file}")
        
        # Precompute lowercase keywords if provided
        keywords_lower = []
        if config.KEYWORDS:
            keywords_lower = [kw.lower() for kw in config.KEYWORDS]
        
        for i, message in enumerate(mbox):
            try:
                email_data = parse_email(message)
                if email_data is None:
                    logger.debug("Email without required fields, skipping")
                    continue

                # Extract subject and content for keyword matching
                subject = email_data.get('subject', '')
                content = email_data.get('content', '')
                
                # Match keywords
                subject_lower = subject.lower() if subject else ""
                content_lower = content.lower() if content and keywords_lower else ""
                extracted_keywords = [kw for kw in keywords_lower 
                                     if (kw in subject_lower) or (content_lower and kw in content_lower)]

                current_batch.append({
                    'message_id': email_data.get('message_id', 'Unknown ID'),
                    'date': email_data.get('date'),
                    'sender': email_data.get('sender', ''),
                    'receiver': email_data.get('receiver', ''),
                    'subject': subject,
                    'content': content,
                    'keywords': ','.join(extracted_keywords)
                })
                
                # When batch is full, yield it and start a new batch
                if len(current_batch) >= batch_size:
                    total_processed += len(current_batch)
                    progress = (total_processed / total_messages) * 100 if total_messages > 0 else 0
                    logger.info(f"Processed {total_processed}/{total_messages} emails ({progress:.1f}%)")
                    
                    yield current_batch
                    current_batch = []
                    
                # Log progress periodically for large files
                if (i + 1) % 5000 == 0:
                    logger.info(f"Processing email {i+1}/{total_messages}")
                
            except EmailParsingError as e:
                logger.error(f"Failed to parse email: {e}")
            except Exception as e:
                message_id = message.get('Message-ID', '(unknown)')
                logger.exception(f"Unexpected error processing email {message_id}: {e}")
                
        # Yield any remaining emails in the final batch
        if current_batch:
            total_processed += len(current_batch)
            progress = (total_processed / total_messages) * 100 if total_messages > 0 else 0
            logger.info(f"Processed {total_processed}/{total_messages} emails ({progress:.1f}%)")
            yield current_batch
            
    except Exception as e:
        logger.exception(f"Error during batch processing: {e}")
        raise
    finally:
        # Ensure mailbox is closed even if an exception occurs
        if mbox is not None:
            mbox.close()
            logger.info(f"Closed mbox file: {mbox_file}")