import sqlite3
import config

def cleanup_database(database_file: str, condition: str):
    """
    Cleans up the database by removing emails that match the given condition.
    
    Args:
        database_file: Path to the SQLite database file.
        condition: SQL condition to match emails for deletion.
    """
    with sqlite3.connect(database_file) as conn:
        cursor = conn.cursor()
        delete_query = f"DELETE FROM emails WHERE {condition}"
        cursor.execute(delete_query)
        rows_affected = cursor.rowcount
        print(f"Deleted {rows_affected} rows matching condition: {condition}")

if __name__ == "__main__":
    # Example usage:
    # Remove emails older than 2022-01-01 or any other condition you want
    cleanup_database(config.DATABASE_FILE, "date < '2022-01-01'")