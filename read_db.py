import sqlite3
import config
import argparse
from typing import Dict, Any, Optional

def read_database(database_file: str, limit: Optional[int] = None, offset: int = 0, 
                 query: Optional[str] = None, order_by: str = "date DESC") -> Optional[Dict[str, Any]]:
    """
    Reads and returns the contents of the emails table from the database.
    
    Args:
        database_file: Path to the SQLite database file.
        limit: Maximum number of rows to retrieve (pagination).
        offset: Number of rows to skip (pagination).
        query: Optional search query to filter emails.
        order_by: Field to order results by.
    
    Returns:
        Dictionary with emails and pagination info, or None if an error occurred.
    """
    try:
        # Validate order_by to prevent SQL injection
        allowed_columns = ["message_id", "date", "sender", "receiver", "subject", "content", "keywords"]
        allowed_directions = ["ASC", "DESC"]
        
        # Parse order_by into column and direction
        parts = order_by.strip().split(" ", 1)
        column = parts[0].lower()
        direction = parts[1].upper() if len(parts) > 1 else "ASC"
        
        if column not in allowed_columns or (len(parts) > 1 and direction not in allowed_directions):
            print(f"Invalid order_by value: {order_by}")
            return None
            
        # Safe order_by string
        safe_order_by = f"{column} {direction}"
        
        with sqlite3.connect(database_file) as conn:
            conn.row_factory = sqlite3.Row  # Enable dictionary access by column name
            cursor = conn.cursor()
            
            base_query = "SELECT * FROM emails"
            params = []
            
            # Add WHERE clause if a query is specified
            if query:
                base_query += " WHERE subject LIKE ? OR sender LIKE ? OR content LIKE ?"
                params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            
            # Add ORDER BY clause
            base_query += f" ORDER BY {safe_order_by}"
            
            # Add LIMIT and OFFSET for pagination
            if limit is not None and limit > 0:
                if limit and limit > 0:
                    base_query += " LIMIT ?"
                    params.append(str(limit))
                base_query += " OFFSET ?" if offset > 0 else ""
                if offset > 0:
                    params.append(str(offset))
            
            cursor.execute(base_query, params)
            
            # Process rows in batches instead of loading all at once
            rows = []
            batch_size = 1000  # Adjust based on typical row size and memory constraints
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                rows.extend([dict(row) for row in batch])
            
            # Get total count for pagination info
            cursor.execute("SELECT COUNT(*) FROM emails" + 
                         (f" WHERE subject LIKE ? OR sender LIKE ? OR content LIKE ?" if query else ""), 
                         [f"%{query}%", f"%{query}%", f"%{query}%"] if query else [])
            total_count = cursor.fetchone()[0]
            
            # Calculate pagination values safely
            current_page = 1
            total_pages = 1
            
            if limit is not None and limit > 0:
                current_page = (offset // limit) + 1
                total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
            
            return {
                'emails': rows,
                'total_count': total_count,
                'page': current_page,
                'total_pages': total_pages,
                'has_next': offset + (limit or 0) < total_count,
                'has_prev': offset > 0
            }
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def display_emails(result: Dict[str, Any]) -> None:
    """
    Displays email results in a formatted way.
    
    Args:
        result: Result dictionary from read_database.
    """
    if not result or not result.get('emails'):
        print("No emails found in the database.")
        return
    
    emails = result['emails']
    print(f"Showing {len(emails)} of {result['total_count']} emails (Page {result['page']}/{result['total_pages']})")
    print("-" * 80)
    
    for email in emails:
        print(f"ID: {email['message_id']}")
        print(f"Date: {email['date']}")
        print(f"From: {email['sender']}")
        print(f"To: {email['receiver']}")
        print(f"Subject: {email['subject']}")
        
        # Show limited content preview
        content = email.get('content', '')
        if content:
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"Content: {preview}")
        
        print("-" * 80)
    
    # Calculate limit from page information to ensure consistency
    limit = len(emails)
    
    # Show pagination info with correct command examples
    if result['has_prev']:
        print(f"Use --offset 0 for first page")
        prev_offset = (result['page'] - 2) * limit
        if prev_offset > 0:
            print(f"Use --offset {prev_offset} for previous page")
        else:
            print(f"Use --offset 0 for previous page")
        
    if result['has_next']:
        next_offset = result['page'] * limit
        print(f"Use --offset {next_offset} for next page")
        print(f"Example: python read_db.py --limit {limit} --offset {next_offset}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query and display emails from the database.")
    parser.add_argument("--db", help=f"Path to database file (default: {config.DATABASE_FILE})",
                      default=config.DATABASE_FILE)
    parser.add_argument("--limit", type=int, help="Maximum number of results to return", default=10)
    parser.add_argument("--offset", type=int, help="Number of results to skip (for pagination)", default=0)
    parser.add_argument("--query", help="Search query to filter emails", default=None)
    parser.add_argument("--order", help="Field to order results by (default: date DESC)", 
                      default="date DESC")
    parser.add_argument("--count-only", action="store_true", help="Only show count of matching emails")
    
    args = parser.parse_args()
    
    if args.count_only:
        result = read_database(args.db, 0, 0, args.query)
        if result:
            print(f"Total emails: {result['total_count']}")
    else:
        result = read_database(args.db, args.limit, args.offset, args.query, args.order)
        if result:
            display_emails(result)
