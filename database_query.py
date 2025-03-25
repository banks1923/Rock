import sqlite3
import pandas as pd
import sys
import csv
import config
import os
from pathlib import Path
from tabulate import tabulate  # You might need to install this: pip install tabulate

def execute_query_command(query, output_file=None, logger=None):
    """
    Execute a SQL query and display or save the results.
    
    Args:
        query (str): The SQL query to execute
        output_file (str, optional): Path to save results as CSV
        logger (logging.Logger, optional): Logger object
    
    Returns:
        int: 0 on success, 1 on failure
    """
    db_path = config.DATABASE_FILE
    
    if not os.path.exists(db_path):
        error_msg = f"Database file not found: {db_path}"
        if logger:
            logger.error(error_msg)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 1
    
    # Basic validation - only allow SELECT queries
    query = query.strip()
    if not query.lower().startswith('select'):
        error_msg = "Only SELECT queries are allowed for security reasons"
        if logger:
            logger.error(error_msg)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 1
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        
        # Execute the query
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # If no results, show message
        if len(df) == 0:
            print("Query executed successfully but returned no results.")
            return 0
        
        # Output results
        if output_file:
            # Save to CSV
            output_path = Path(output_file)
            df.to_csv(output_path, index=False)
            print(f"Results saved to {output_path} ({len(df)} rows)")
        else:
            # Print to console in a nice table format
            print(tabulate(df.values.tolist(), headers=df.columns.tolist(), tablefmt='psql', showindex=False))
            print(f"\nTotal: {len(df)} rows")
        
        return 0
    except Exception as e:
        error_msg = f"Query execution failed: {str(e)}"
        if logger:
            logger.exception(error_msg)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 1

def get_table_info():
    """Get information about database tables."""
    db_path = config.DATABASE_FILE
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}", file=sys.stderr)
        return 1
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("Available tables:")
        for table in tables:
            # Get column info for each table
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\n{table}:")
            print("  Columns:")
            for col in columns:
                print(f"    {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            print(f"  Row count: {row_count}")
        
        conn.close()
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

def get_database_stats(logger=None):
    """
    Get statistics about the database contents.
    
    Args:
        logger (logging.Logger, optional): Logger object
    
    Returns:
        dict: Statistics about database contents
    """
    db_path = config.DATABASE_FILE
    stats = {}
    
    if not os.path.exists(db_path):
        error_msg = f"Database file not found: {db_path}"
        if logger:
            logger.error(error_msg)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        stats['error'] = error_msg
        return stats
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        stats['tables'] = tables
        
        # Get email count
        if 'emails' in tables:
            cursor.execute("SELECT COUNT(*) FROM emails")
            stats['total_emails'] = cursor.fetchone()[0]
        else:
            stats['total_emails'] = 0
        
        # Get thread count
        if 'email_threads' in tables:
            cursor.execute("SELECT COUNT(*) FROM email_threads")
            stats['total_threads'] = cursor.fetchone()[0]
        else:
            stats['total_threads'] = 0
        
        # Get attachment count if exists
        if 'attachments' in tables:
            cursor.execute("SELECT COUNT(*) FROM attachments")
            stats['total_attachments'] = cursor.fetchone()[0]
        
        # Get DB file size
        stats['db_size_kb'] = os.path.getsize(db_path) // 1024
        
        conn.close()
        return stats
    except Exception as e:
        error_msg = f"Failed to get database statistics: {str(e)}"
        if logger:
            logger.exception(error_msg)
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        stats['error'] = error_msg
        return stats

if __name__ == "__main__":
    # This allows running queries directly:
    # python database_query.py "SELECT * FROM emails LIMIT 10"
    if len(sys.argv) < 2:
        print("Usage: python database_query.py \"SQL_QUERY\" [output_file.csv]")
        print("       python database_query.py --info")
        print("       python database_query.py --stats")
        sys.exit(1)
    
    if sys.argv[1] == '--info':
        sys.exit(get_table_info())
    
    if sys.argv[1] == '--stats':
        stats = get_database_stats()
        print("\nDatabase Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        sys.exit(0)
    
    query = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    sys.exit(execute_query_command(query, output_file))
