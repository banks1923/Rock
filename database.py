import sqlite3
import logging
import time
from typing import List, Dict, Any, Optional
from exceptions import DatabaseError
import config
import os

logger = logging.getLogger(__name__)

def create_database(database_file: str) -> bool:
    """
    Creates the SQLite database and table if they don't exist.

    Args:
        database_file: Path to the database file

    Returns:
        True if successful, raises an error otherwise.
        
    Raises:
        DatabaseError: If an error occurs during database creation.
    """
    logger.info(f"Creating database: {database_file}")
    try:
        with sqlite3.connect(database_file) as conn:
            # Create emails table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    date DATETIME,
                    sender TEXT,
                    receiver TEXT,
                    subject TEXT,
                    content TEXT,
                    keywords TEXT,
                    thread_id TEXT
                )
            ''')
            # If table exists from a previous version, ensure thread_id column is present
            cursor = conn.execute("PRAGMA table_info(emails)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'thread_id' not in columns:
                logger.info("Adding missing 'thread_id' column to emails table")
                conn.execute("ALTER TABLE emails ADD COLUMN thread_id TEXT")
            
            # Create indices for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON emails(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_thread_id ON emails(thread_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sender ON emails(sender)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_subject ON emails(subject)')
            
            # Create thread metadata table
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
            
            conn.commit()
            logger.info("Database schema created successfully")
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
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA cache_size = 10000")
            
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
                        email['content'],
                        email['keywords'],
                        email.get('thread_id', None)  # Add thread_id to the insert
                    )
                    for email in batch
                ]

                # Begin transaction for this batch
                cursor = conn.cursor()
                
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO emails (
                        message_id, date, sender, receiver, subject, content, keywords, thread_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    if not emails or not thread_id:
        return True
        
    try:
        # Extract thread metadata from emails
        subjects = [e.get('subject', '') for e in emails if e.get('subject')]
        normalized_subject = subjects[0] if subjects else ""
        
        senders = set(e.get('sender', '') for e in emails if e.get('sender'))
        receivers = set(e.get('receiver', '') for e in emails if e.get('receiver'))
        participants = ','.join(sorted(filter(None, senders.union(receivers))))
        
        dates = [e.get('date') for e in emails if e.get('date') is not None]
        start_date = min(d for d in dates if d is not None) if dates else None
        last_update = max(d for d in dates if d is not None) if dates else None
        
        with sqlite3.connect(database_file) as conn:
            # Insert or replace thread metadata
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
            message_ids = [email.get('message_id') for email in emails if email.get('message_id')]
            if message_ids:
                # Use parameter substitution for SQL safety
                placeholders = ','.join(['?'] * len(message_ids))
                conn.execute(f"""
                    UPDATE emails SET thread_id = ? 
                    WHERE message_id IN ({placeholders})
                """, [thread_id] + message_ids)
            
            conn.commit()
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error updating thread info: {e}")
        raise DatabaseError(f"Error updating thread info: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error updating thread info: {e}")
        raise DatabaseError(f"Error updating thread info: {e}") from e

def get_thread_emails(thread_id: str, database_file: str) -> List[Dict[str, Any]]:
    """
    Retrieve all emails belonging to a specific thread.
    
    Args:
        thread_id: The thread identifier
        database_file: Path to the database file
        
    Returns:
        List of email dictionaries in the thread
        
    Raises:
        DatabaseError: On database errors
    """
    try:
        with sqlite3.connect(database_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM emails 
                WHERE thread_id = ? 
                ORDER BY date ASC
            """, (thread_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving thread emails: {e}")
        raise DatabaseError(f"Error retrieving thread emails: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error retrieving thread emails: {e}")
        raise DatabaseError(f"Error retrieving thread emails: {e}") from e

def validate_database(database_file: str) -> Dict[str, Any]:
    """
    Validates that the database exists and has the correct schema.
    
    Args:
        database_file: Path to the database file
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "exists": False,
        "valid": False,
        "tables": [],
        "errors": []
    }
    
    if not os.path.exists(database_file):
        results["errors"].append(f"Database file not found: {database_file}")
        return results
        
    results["exists"] = True
    
    try:
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            results["tables"] = tables
            
            required_tables = ["emails"]
            for table in required_tables:
                if table not in tables:
                    results["errors"].append(f"Required table not found: {table}")
                    
            # Check email count
            if "emails" in tables:
                cursor.execute("SELECT COUNT(*) FROM emails")
                results["email_count"] = cursor.fetchone()[0]
            
            results["valid"] = len(results["errors"]) == 0
    except Exception as e:
        results["errors"].append(f"Error validating database: {str(e)}")
        results["valid"] = False
        
    return results
