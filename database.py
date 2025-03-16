import sqlite3
import logging
import time
from typing import List, Dict, Any
from exceptions import DatabaseError
import config

logger = logging.getLogger(__name__)

def create_database(database_file: str) -> bool:
    """
    Creates the SQLite database and table if they don't exist.

    Returns:
        True if successful, raises an error otherwise.
    Raises:
        DatabaseError: If an error occurs during database creation.
    """
    logger.info(f"Creating database: {database_file}")
    try:
        with sqlite3.connect(database_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    date DATETIME,
                    sender TEXT,
                    receiver TEXT,
                    subject TEXT,
                    content TEXT,
                    keywords TEXT
                )
            ''')
            # Create an index on the date column to optimize timeline queries
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_date ON emails(date)
            ''')
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error while creating database: {e}")
        raise DatabaseError(f"Error creating database: {e}") from e
    except Exception as e:
        logger.exception(f"Unexpected error creating database: {e}")
        raise DatabaseError(f"Error creating database: {e}") from e

def insert_email_data(emails: List[Dict[str, Any]], database_file: str, batch_size: int = 500) -> int:
    """
    Inserts email data into the SQLite database with optimized batching.

    Args:
        emails: A list of email dictionaries.
        database_file: The path to the database file.
        batch_size: Number of records to insert in a single batch.
    Returns:
        The number of rows inserted.
    Raises:
        DatabaseError: on database errors
    """
    if not emails:
        logger.info("No emails to insert")
        return 0
        
    logger.info(f"Inserting {len(emails)} email records into database: {database_file}")
    
    total_inserted = 0
    start_time = time.time()
    
    try:
        with sqlite3.connect(database_file) as conn:
            # Enable WAL mode for better concurrent performance
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Process emails in batches
            for i in range(0, len(emails), batch_size):
                batch = emails[i:i+batch_size]
                
                data_to_insert = [
                    (
                        email['message_id'],
                        email['date'].isoformat() if email['date'] and hasattr(email['date'], 'isoformat') else email['date'],
                        email['sender'],
                        email['receiver'],
                        email['subject'],
                        email['content'],   # Using 'content' (consistent with the parser)
                        email['keywords'],
                    )
                    for email in batch
                ]

                # Begin transaction for this batch
                cursor = conn.cursor()
                
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO emails (
                        message_id, date, sender, receiver, subject, content, keywords
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    data_to_insert,
                )
                
                batch_inserted = cursor.rowcount
                total_inserted += batch_inserted
                
                # Log progress for large datasets
                if len(emails) > batch_size:
                    processed_percent = min(100, round((i + len(batch)) / len(emails) * 100, 1))
                    logger.info(f"Inserted batch: {batch_inserted} rows - {processed_percent}% complete")

        elapsed_time = time.time() - start_time
        rate = total_inserted / elapsed_time if elapsed_time > 0 else 0
        logger.info(f"Database insertion completed: {total_inserted} rows in {elapsed_time:.2f}s ({rate:.1f} rows/sec)")
        return total_inserted

    except sqlite3.Error as e:
        logger.exception(f"SQLite error inserting data: {e}")
        raise DatabaseError(f"Error inserting data: {e}") from e
    except Exception as e:
        logger.exception(f"Unexpected error inserting data: {e}")
        raise DatabaseError(f"Error inserting data: {e}") from e

def update_database_schema(database_file: str) -> bool:
    """
    Updates the database schema to add support for email threading.
    
    Args:
        database_file: Path to the SQLite database file
    
    Returns:
        True if successful
    
    Raises:
        DatabaseError: If an error occurs during schema update
    """
    logger.info(f"Updating database schema: {database_file}")
    try:
        with sqlite3.connect(database_file) as conn:
            # Check if thread_id column already exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(emails)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'thread_id' not in columns:
                logger.info("Adding thread_id column to emails table")
                conn.execute("ALTER TABLE emails ADD COLUMN thread_id TEXT")
                # Create an index on thread_id for thread queries
                conn.execute("CREATE INDEX idx_thread_id ON emails(thread_id)")
            
            # Add a new table for thread metadata if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_threads (
                    thread_id TEXT PRIMARY KEY,
                    subject TEXT,
                    participants TEXT,
                    start_date DATETIME,
                    last_update DATETIME,
                    message_count INTEGER
                )
            ''')
            
            return True
            
    except sqlite3.Error as e:
        logger.error(f"Database error while updating schema: {e}")
        raise DatabaseError(f"Error updating database schema: {e}") from e
    except Exception as e:
        logger.exception(f"Unexpected error updating database schema: {e}")
        raise DatabaseError(f"Error updating database schema: {e}") from e

def update_thread_info(thread_id: str, emails: List[Dict[str, Any]], database_file: str) -> bool:
    """
    Update or insert thread metadata in the database.
    
    Args:
        thread_id: Thread identifier
        emails: List of email dictionaries in the thread
        database_file: Path to the database file
    
    Returns:
        True if successful
    
    Raises:
        DatabaseError: On database errors
    """
    if not emails:
        return True
        
    try:
        # Extract thread metadata from emails
        subjects = [e.get('subject', '') for e in emails if e.get('subject')]
        normalized_subject = subjects[0] if subjects else ""
        
        senders = set([e.get('sender', '') for e in emails if e.get('sender')])
        receivers = set([e.get('receiver', '') for e in emails if e.get('receiver')])
        participants = ','.join(sorted(senders.union(receivers)))
        
        # Find earliest and latest dates
        dates = [e.get('date') for e in emails if e.get('date')]
        start_date = min(dates) if dates else None
        last_update = max(dates) if dates else None
        
        with sqlite3.connect(database_file) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO email_threads 
                (thread_id, subject, participants, start_date, last_update, message_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                normalized_subject,
                participants,
                start_date.isoformat() if start_date and hasattr(start_date, 'isoformat') else start_date,
                last_update.isoformat() if last_update and hasattr(last_update, 'isoformat') else last_update,
                len(emails)
            ))
            
            # Update thread_id for all emails in the thread
            cursor = conn.cursor()
            for email in emails:
                if email.get('message_id'):
                    cursor.execute("""
                        UPDATE emails SET thread_id = ? WHERE message_id = ?
                    """, (thread_id, email['message_id']))
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error updating thread info: {e}")
        raise DatabaseError(f"Error updating thread info: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error updating thread info: {e}")
        raise DatabaseError(f"Error updating thread info: {e}") from e
