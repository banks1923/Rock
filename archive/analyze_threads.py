"""
Tool to analyze and manage email threads in the database.
"""
import sqlite3
import argparse
import logging
import sys
from typing import Dict, List, Any, Optional
import config
from database import update_database_schema
from thread_utils import ThreadIdentifier

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_threads(database_file: str) -> Dict[str, Any]:
    """
    Analyze email threads in the database and return statistics.
    
    Args:
        database_file: Path to the database file
    
    Returns:
        Dictionary of thread statistics
    """
    stats = {
        "total_emails": 0,
        "threaded_emails": 0,
        "thread_count": 0,
        "avg_thread_size": 0,
        "largest_thread": 0,
        "singleton_threads": 0,
    }
    
    try:
        with sqlite3.connect(database_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if thread columns exist
            cursor.execute("PRAGMA table_info(emails)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'thread_id' not in columns:
                logger.info("Thread support not enabled in database. Enabling now...")
                update_database_schema(database_file)
            
            # Get total email count
            cursor.execute("SELECT COUNT(*) FROM emails")
            stats["total_emails"] = cursor.fetchone()[0]
            
            # Get thread statistics
            cursor.execute("""
                SELECT COUNT(*) FROM emails WHERE thread_id IS NOT NULL
            """)
            stats["threaded_emails"] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT thread_id) FROM emails WHERE thread_id IS NOT NULL
            """)
            stats["thread_count"] = cursor.fetchone()[0]
            
            if stats["thread_count"] > 0:
                stats["avg_thread_size"] = stats["threaded_emails"] / stats["thread_count"]
            
            # Find largest thread
            cursor.execute("""
                SELECT thread_id, COUNT(*) as count
                FROM emails
                WHERE thread_id IS NOT NULL
                GROUP BY thread_id
                ORDER BY count DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                stats["largest_thread"] = row["count"]
            
            # Count singleton threads
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT thread_id, COUNT(*) as count
                    FROM emails
                    WHERE thread_id IS NOT NULL
                    GROUP BY thread_id
                    HAVING count = 1
                )
            """)
            stats["singleton_threads"] = cursor.fetchone()[0]
            
        return stats
        
    except sqlite3.Error as e:
        logger.error(f"Database error analyzing threads: {e}")
        return stats
    except Exception as e:
        logger.error(f"Error analyzing threads: {e}")
        return stats

def rebuild_threads(database_file: str, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Rebuild thread information for all emails in the database.
    
    Args:
        database_file: Path to the database file
        batch_size: Number of emails to process in each batch
        
    Returns:
        Statistics about the rebuild process
    """
    stats = {
        "processed": 0,
        "threads_created": 0,
        "emails_threaded": 0,
        "errors": 0
    }
    
    thread_identifier = ThreadIdentifier()
    
    try:
        with sqlite3.connect(database_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Ensure thread support is enabled
            update_database_schema(database_file)
            
            # Reset thread assignments
            cursor.execute("UPDATE emails SET thread_id = NULL")
            cursor.execute("DELETE FROM email_threads")
            
            # Process emails in batches
            offset = 0
            thread_groups = {}
            
            while True:
                cursor.execute("""
                    SELECT * FROM emails
                    LIMIT ? OFFSET ?
                """, (batch_size, offset))
                
                rows = cursor.fetchall()
                if not rows:
                    break
                
                # Process this batch
                for row in rows:
                    email_data = dict(row)
                    thread_id = thread_identifier.identify_thread(email_data)
                    
                    # Store in thread groups
                    thread_groups.setdefault(thread_id, []).append(email_data)
                    stats["processed"] += 1
                
                offset += batch_size
                logger.info(f"Processed {stats['processed']} emails")
            
            # Update thread information in database
            stats["threads_created"] = len(thread_groups)
            
            for thread_id, emails in thread_groups.items():
                try:
                    # Extract thread metadata
                    subjects = [e.get('subject', '') for e in emails if e.get('subject')]
                    normalized_subject = subjects[0] if subjects else ""
                    
                    # Update emails with thread ID
                    email_ids = [(thread_id, e['message_id']) for e in emails if e.get('message_id')]
                    cursor.executemany("""
                        UPDATE emails SET thread_id = ? WHERE message_id = ?
                    """, email_ids)
                    
                    stats["emails_threaded"] += len(email_ids)
                    
                except Exception as e:
                    logger.error(f"Error processing thread {thread_id}: {e}")
                    stats["errors"] += 1
            
            # Commit all changes
            conn.commit()
            
        return stats
        
    except sqlite3.Error as e:
        logger.error(f"Database error rebuilding threads: {e}")
        return stats
    except Exception as e:
        logger.error(f"Error rebuilding threads: {e}")
        return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and manage email threads")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing thread information")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild thread information")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    parser.add_argument("--db", default=config.DATABASE_FILE, help="Path to database file")
    
    args = parser.parse_args()
    
    if args.analyze:
        stats = analyze_threads(args.db)
        print("\nThread Analysis Results:")
        print("========================")
        print(f"Total emails: {stats['total_emails']}")
        print(f"Emails in threads: {stats['threaded_emails']}")
        print(f"Distinct threads: {stats['thread_count']}")
        print(f"Average thread size: {stats['avg_thread_size']:.2f} emails")
        print(f"Largest thread: {stats['largest_thread']} emails")
        print(f"Singleton threads: {stats['singleton_threads']}")
        print("========================")
        
    elif args.rebuild:
        print(f"Rebuilding thread information in {args.db}")
        stats = rebuild_threads(args.db, args.batch_size)
        print("\nThread Rebuild Results:")
        print("=======================")
        print(f"Emails processed: {stats['processed']}")
        print(f"Threads created: {stats['threads_created']}")
        print(f"Emails assigned to threads: {stats['emails_threaded']}")
        print(f"Errors encountered: {stats['errors']}")
        print("=======================")
        
    else:
        parser.print_help()
        sys.exit(1)
