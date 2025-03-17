import sqlite3
import csv
import config
import os
from typing import Optional

def export_to_csv(database_file: str, output_file: str = "emails_export.csv", batch_size: int = 1000) -> Optional[str]:
    """
    Exports email data from the database to a CSV file using batched processing for memory efficiency.
    
    Args:
        database_file: Path to the SQLite database file.
        output_file: Path to the output CSV file.
        batch_size: Number of rows to process in each batch.
        
    Returns:
        Path to the output file on success, None on failure.
    """
    try:
        # Validate batch_size
        if batch_size <= 0:
            print("Batch size must be a positive integer")
            batch_size = 1000
            
        if not os.path.exists(database_file):
            print(f"Error: Database file {database_file} does not exist.")
            return None
            
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # Get column names first
            cursor.execute("PRAGMA table_info(emails)")
            column_names = [info[1] for info in cursor.fetchall()]
            
            # Get total count for progress reporting
            cursor.execute("SELECT COUNT(*) FROM emails")
            total_count = cursor.fetchone()[0]
            
            if total_count == 0:
                print("No emails found in the database.")
                return output_file
                
            print(f"Exporting {total_count} emails to CSV...")
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                
                # Process in batches to prevent memory issues
                processed = 0
                offset = 0
                
                while True:
                    # Use parameterized query to prevent SQL injection
                    cursor.execute("SELECT * FROM emails LIMIT ? OFFSET ?", (batch_size, offset))
                    rows = cursor.fetchall()
                    
                    if not rows:
                        break
                        
                    for row in rows:
                        writer.writerow(row)
                    
                    processed += len(rows)
                    print(f"Exported {processed}/{total_count} emails ({processed/total_count*100:.1f}%)")
                    
                    offset += batch_size
                    
                    if len(rows) < batch_size:
                        break
                
            print(f"Successfully exported {processed} rows to {output_file}")
            return output_file
            
    except sqlite3.Error as e:
        print(f"Database error during export: {e}")
        return None
    except IOError as e:
        print(f"I/O error during export: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during export: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export emails from database to CSV")
    parser.add_argument("--output", "-o", help="Output CSV file", default="emails_export.csv")
    parser.add_argument("--batch", "-b", type=int, help="Batch size", default=1000)
    args = parser.parse_args()
    
    export_to_csv(config.DATABASE_FILE, args.output, args.batch)