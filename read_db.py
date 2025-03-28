import sqlite3
import config
import os
import datetime
from typing import Dict, Any, Optional, Tuple, List
from ocr_utils import process_attachment_ocr

def get_attachment_data(database_file: str, message_id: int, filename: str) -> Optional[Tuple[bytes, str]]:
    """
    Retrieves attachment data from the database.
    
    Args:
        database_file: Path to the SQLite database file.
        message_id: The ID of the email message.
        filename: The filename of the attachment.
        
    Returns:
        Tuple of (attachment_data, mime_type) or None if not found.
    """
    try:
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # Query to get attachment data and MIME type
            cursor.execute(
                "SELECT attachment_data, mime_type FROM email_attachments WHERE message_id = ? AND filename = ?",
                (message_id, filename)
            )
            
            result = cursor.fetchone()
            if result:
                return (result[0], result[1])
            return None
            
    except sqlite3.Error as e:
        print(f"SQLite error retrieving attachment: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error retrieving attachment: {e}")
        return None

def get_email_attachments(database_file: str, message_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves attachment metadata for an email.
    
    Args:
        database_file: Path to the SQLite database file.
        message_id: The ID of the email message.
        
    Returns:
        List of attachment metadata dictionaries.
    """
    try:
        with sqlite3.connect(database_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Query to get attachment metadata (excluding binary data)
            cursor.execute(
                "SELECT attachment_id, filename, mime_type, size FROM email_attachments WHERE message_id = ?",
                (message_id,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
    except sqlite3.Error as e:
        print(f"SQLite error retrieving attachment list: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error retrieving attachment list: {e}")
        return []

def get_attachment_text(database_file: str, attachment_id: int) -> Optional[str]:
    """
    Retrieves OCR text for an attachment if available.
    
    Args:
        database_file: Path to the SQLite database file.
        attachment_id: The ID of the attachment.
        
    Returns:
        OCR text or None if not available.
    """
    try:
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # First check if we already have OCR text stored
            cursor.execute(
                "SELECT ocr_text FROM attachment_ocr WHERE attachment_id = ?",
                (attachment_id,)
            )
            
            result = cursor.fetchone()
            if result and result[0]:
                return result[0]
            
            # If no OCR text found, return None
            return None
            
    except sqlite3.Error as e:
        print(f"SQLite error retrieving OCR text: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error retrieving OCR text: {e}")
        return None

def process_attachment_for_ocr(database_file: str, attachment_id: int) -> Optional[str]:
    """
    Process an attachment for OCR and store the results.
    
    Args:
        database_file: Path to the SQLite database file.
        attachment_id: The ID of the attachment.
        
    Returns:
        OCR text or None if processing failed.
    """
    try:
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # Get attachment data
            cursor.execute(
                "SELECT attachment_data, mime_type, filename FROM email_attachments WHERE attachment_id = ?",
                (attachment_id,)
            )
            
            result = cursor.fetchone()
            if not result:
                return None
                
            attachment_data, mime_type, filename = result
            
            # Process through OCR
            from ocr_utils import process_attachment_ocr
            ocr_text = process_attachment_ocr(attachment_data, mime_type, filename)
            
            if ocr_text:
                # Store OCR text in database
                cursor.execute(
                    "INSERT OR REPLACE INTO attachment_ocr (attachment_id, ocr_text) VALUES (?, ?)",
                    (attachment_id, ocr_text)
                )
                conn.commit()
                
                return ocr_text
            
            return None
            
    except sqlite3.Error as e:
        print(f"SQLite error processing OCR: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error processing OCR: {e}")
        return None

def read_database(database_file: str, limit: Optional[int] = None, offset: int = 0, 
                 query: Optional[str] = None, order_by: str = "date DESC",
                 include_ocr: bool = True) -> Optional[Dict[str, Any]]:
    """
    Reads and returns the contents of the emails table from the database.
    
    Args:
        database_file: Path to the SQLite database file.
        limit: Maximum number of rows to retrieve (pagination).
        offset: Number of rows to skip (pagination).
        query: Optional search query to filter emails.
        order_by: Field to order results by.
        include_ocr: Whether to include OCR text for attachments.
    
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
                
                email_rows = []
                for row in batch:
                    email_dict = dict(row)
                    
                    # Add attachments metadata if they exist
                    attachments = get_email_attachments(database_file, email_dict['message_id'])
                    
                    if attachments:
                        # If OCR is requested, include OCR text with attachments
                        if include_ocr:
                            for attachment in attachments:
                                # Get OCR text if available
                                ocr_text = get_attachment_text(database_file, attachment['attachment_id'])
                                if ocr_text:
                                    attachment['ocr_text'] = ocr_text
                                
                        email_dict['attachments'] = attachments
                        
                    email_rows.append(email_dict)
                
                rows.extend(email_rows)
            
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

def import_pdf_file(database_file: str, pdf_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    Import a PDF file into the database as a standalone document.
    
    Args:
        database_file: Path to the SQLite database file.
        pdf_path: Path to the PDF file to import.
        metadata: Optional dictionary with metadata (date, title, source, etc).
        
    Returns:
        The document ID of the imported PDF if successful, None otherwise.
    """
    try:
        if not os.path.exists(pdf_path) or not pdf_path.lower().endswith('.pdf'):
            print(f"Invalid PDF file: {pdf_path}")
            return None
            
        # Read the PDF file as binary data
        with open(pdf_path, 'rb') as file:
            pdf_data = file.read()
            
        # Extract filename from path
        filename = os.path.basename(pdf_path)
        
        # Prepare metadata with defaults
        meta = {
            'date': datetime.datetime.now().isoformat(),
            'title': filename,
            'source': 'direct_import',
            'tags': '',
            'notes': ''
        }
        
        # Update with provided metadata if any
        if metadata:
            meta.update(metadata)
            
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # First check if we need to create the pdf_documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdf_documents (
                    document_id INTEGER PRIMARY KEY,
                    filename TEXT NOT NULL,
                    date TEXT,
                    title TEXT,
                    source TEXT,
                    tags TEXT,
                    notes TEXT,
                    file_size INTEGER,
                    creation_date TEXT
                )
            """)
            
            # Create table for PDF data if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdf_document_data (
                    document_id INTEGER PRIMARY KEY,
                    pdf_data BLOB,
                    ocr_text TEXT,
                    ocr_processed INTEGER DEFAULT 0,
                    FOREIGN KEY(document_id) REFERENCES pdf_documents(document_id)
                )
            """)
            
            # Insert document metadata
            cursor.execute("""
                INSERT INTO pdf_documents 
                (filename, date, title, source, tags, notes, file_size, creation_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, 
                (
                    filename, 
                    meta['date'], 
                    meta['title'], 
                    meta['source'], 
                    meta['tags'], 
                    meta['notes'],
                    len(pdf_data),
                    datetime.datetime.now().isoformat()
                )
            )
            
            # Get the document ID
            document_id = cursor.lastrowid
            
            # Store the PDF data
            cursor.execute("""
                INSERT INTO pdf_document_data (document_id, pdf_data)
                VALUES (?, ?)
                """,
                (document_id, pdf_data)
            )
            
            conn.commit()
            
            print(f"Successfully imported PDF: {filename} (ID: {document_id})")
            return document_id
            
    except sqlite3.Error as e:
        print(f"SQLite error importing PDF: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error importing PDF: {e}")
        return None

def process_pdf_for_ocr(database_file: str, document_id: int) -> Optional[str]:
    """
    Process a PDF document for OCR and store the results.
    
    Args:
        database_file: Path to the SQLite database file.
        document_id: The ID of the PDF document.
        
    Returns:
        OCR text or None if processing failed.
    """
    try:
        with sqlite3.connect(database_file) as conn:
            cursor = conn.cursor()
            
            # Get PDF data
            cursor.execute(
                "SELECT pdf_data FROM pdf_document_data WHERE document_id = ?",
                (document_id,)
            )
            
            result = cursor.fetchone()
            if not result:
                return None
                
            pdf_data = result[0]
            
            # Get filename for better OCR processing
            cursor.execute(
                "SELECT filename FROM pdf_documents WHERE document_id = ?",
                (document_id,)
            )
            
            filename_result = cursor.fetchone()
            if not filename_result:
                filename = f"document_{document_id}.pdf"
            else:
                filename = filename_result[0]
            
            # Process through OCR
            ocr_text = process_attachment_ocr(pdf_data, "application/pdf", filename)
            
            if ocr_text:
                # Store OCR text in database
                cursor.execute(
                    "UPDATE pdf_document_data SET ocr_text = ?, ocr_processed = 1 WHERE document_id = ?",
                    (ocr_text, document_id)
                )
                conn.commit()
                
                return ocr_text
            
            return None
            
    except sqlite3.Error as e:
        print(f"SQLite error processing PDF OCR: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error processing PDF OCR: {e}")
        return None

def get_pdf_documents(database_file: str, limit: Optional[int] = None, offset: int = 0,
                     query: Optional[str] = None, order_by: str = "date DESC") -> Optional[Dict[str, Any]]:
    """
    Retrieve PDF documents from the database.
    
    Args:
        database_file: Path to the SQLite database file.
        limit: Maximum number of documents to retrieve.
        offset: Number of documents to skip.
        query: Optional search query.
        order_by: Field to order results by.
        
    Returns:
        Dictionary with PDF documents and pagination info.
    """
    try:
        # Validate order_by to prevent SQL injection
        allowed_columns = ["document_id", "filename", "date", "title", "source", "file_size", "creation_date"]
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
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pdf_documents'")
            if not cursor.fetchone():
                return {'documents': [], 'total_count': 0, 'page': 1, 'total_pages': 0, 'has_next': False, 'has_prev': False}
            
            base_query = """
                SELECT d.*, 
                       CASE WHEN pd.ocr_processed = 1 THEN 1 ELSE 0 END as has_ocr 
                FROM pdf_documents d 
                LEFT JOIN pdf_document_data pd ON d.document_id = pd.document_id
            """
            params = []
            
            # Add WHERE clause if a query is specified
            if query:
                # Fixed: Add proper parentheses around conditions
                base_query += " WHERE (d.title LIKE ? OR d.filename LIKE ? OR d.notes LIKE ? OR d.tags LIKE ?"
                params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
                
                # Also search in OCR text if available
                base_query += " OR pd.ocr_text LIKE ?)"
                params.append(f"%{query}%")
            
            # Add ORDER BY clause
            base_query += f" ORDER BY d.{safe_order_by}"
            
            # Add LIMIT and OFFSET for pagination
            if limit is not None and limit > 0:
                base_query += " LIMIT ?"
                # Fixed: Convert limit to string to avoid type issues
                params.append(str(limit))
                
            if offset > 0:
                base_query += " OFFSET ?"
                # Fixed: Convert offset to string to avoid type issues
                params.append(str(offset))
            
            cursor.execute(base_query, params)
            documents = [dict(row) for row in cursor.fetchall()]
            
            # Get total count for pagination info
            # Fixed: Update count query to match the main query including OCR text
            count_query = "SELECT COUNT(*) FROM pdf_documents d LEFT JOIN pdf_document_data pd ON d.document_id = pd.document_id"
            if query:
                count_query += " WHERE (d.title LIKE ? OR d.filename LIKE ? OR d.notes LIKE ? OR d.tags LIKE ? OR pd.ocr_text LIKE ?)"
                cursor.execute(count_query, [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
            else:
                cursor.execute(count_query)
                
            total_count = cursor.fetchone()[0]
            
            # Calculate pagination values safely
            current_page = 1
            total_pages = 1
            
            if limit is not None and limit > 0:
                current_page = (offset // limit) + 1
                total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
            
            return {
                'documents': documents,
                'total_count': total_count,
                'page': current_page,
                'total_pages': total_pages,
                'has_next': offset + (limit or 0) < total_count,
                'has_prev': offset > 0
            }
            
    except sqlite3.Error as e:
        print(f"SQLite error retrieving PDF documents: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error retrieving PDF documents: {e}")
        return None

# Simplified main function
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database access API - primarily for web interface.")
    parser.add_argument("--import-pdf", metavar="PDF_PATH", help="Import a PDF file into the database")
    parser.add_argument("--process-ocr", metavar="ATTACHMENT_ID", type=int, help="Process attachment OCR")
    parser.add_argument("--process-pdf-ocr", metavar="DOCUMENT_ID", type=int, help="Process PDF OCR")
    
    args = parser.parse_args()
    
    if args.import_pdf:
        document_id = import_pdf_file(config.DATABASE_FILE, args.import_pdf)
        if document_id:
            print(f"Successfully imported PDF: ID={document_id}")
            
    elif args.process_ocr:
        result = process_attachment_for_ocr(config.DATABASE_FILE, args.process_ocr)
        if result:
            print(f"OCR processing successful: {len(result)} characters extracted")
            
    elif args.process_pdf_ocr:
        result = process_pdf_for_ocr(config.DATABASE_FILE, args.process_pdf_ocr)
        if result:
            print(f"PDF OCR processing successful: {len(result)} characters extracted")
