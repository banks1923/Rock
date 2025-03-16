import sqlite3
import config
from datetime import datetime
import logging
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from text_utils import TextCleaner
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pdf_report')

def generate_pdf_report(output_file: str = "report.pdf", 
                       cleaning_options=None, 
                       batch_size: int = 100,
                       max_emails: int = 100,
                       include_details: bool = True,
                       compress: bool = True,
                       columns: list = [],
                       sort_by: str = "date DESC"):
    """
    Generates a PDF report from the email data in the database with optimized memory usage.
    
    Args:
        output_file: Path to the output PDF file.
        cleaning_options: Dict of text cleaning options.
        batch_size: Number of emails to process in each batch for memory efficiency.
        max_emails: Maximum number of emails to include in the detailed section.
        include_details: Whether to include detailed email contents.
        compress: Whether to compress the PDF.
        columns: List of columns to include in the summary table.
        sort_by: Column and direction to sort by.
    """
    print(f"Starting to generate PDF report to {output_file}...")
    start_time = datetime.now()
    
    # Initialize the text cleaner with caching to avoid repeated processing
    cleaner = TextCleaner(cleaning_options)
    cleaned_cache = {}  # Cache for cleaned email bodies
    
    # Set default columns if not specified
    if columns is None:
        columns = ["message_id", "date", "sender", "subject"]
    
    try:
        conn = sqlite3.connect(config.DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check for body column
        cursor.execute("PRAGMA table_info(emails)")
        columns_info = {col[1]: col[0] for col in cursor.fetchall()}
        
        # Find possible body column names
        body_column = None
        for col in ['content', 'body', 'message', 'text', 'email_body', 'message_text']:
            if col in columns_info:
                body_column = col
                print(f"Found body column: {body_column}")
                break
                
        # Get total count for progress reporting
        cursor.execute("SELECT COUNT(*) FROM emails")
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            print("No emails found in the database.")
            return
            
        print(f"Found {total_count} emails to process.")
        
        # Create the PDF document with compression if requested
        pdf_dir = os.path.dirname(os.path.abspath(output_file))
        if pdf_dir and not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir, exist_ok=True)
            
        doc = SimpleDocTemplate(
            output_file, 
            pagesize=A4, 
            leftMargin=0.5*inch, 
            rightMargin=0.5*inch,
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch,
            compress=compress
        )
        
        # Cache styles for reuse
        styles = getSampleStyleSheet()
        
        # Create custom styles once
        if 'TableCell' not in styles:
            styles.add(ParagraphStyle(
                name='TableCell',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                wordWrap='CJK'
            ))
        
        if 'EmailBody' not in styles:  
            styles.add(ParagraphStyle(
                name='EmailBody',
                parent=styles['Normal'],
                fontSize=9,
                leading=12,
                leftIndent=12,
                rightIndent=12,
                alignment=TA_JUSTIFY,
                spaceAfter=12
            ))
        
        elements = []
        
        # Add report header
        current_date = datetime.now().strftime("%b %d, %Y at %H:%M:%S")
        
        # Try to add logo if exists
        logo_path = Path(__file__).parent / "logo.png"
        if (logo_path).exists():
            logo = Image(str(logo_path), width=1.5*inch, height=0.5*inch)
            elements.append(logo)
            elements.append(Spacer(1, 12))
            
        elements.append(Paragraph("Email Summary Report", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Report generated on: {current_date}", styles["Normal"]))
        elements.append(Paragraph(f"Total emails: {total_count}", styles["Normal"]))
        elements.append(Spacer(1, 12))
        
        # Validate batch_size
        if batch_size <= 0:
            logger.warning("Invalid batch size, using default of 100")
            batch_size = 100
        
        # First section: Summary table (in batches to save memory)
        print("Generating summary table...")
        
        # Create header row based on selected columns
        column_labels = {
            "message_id": "ID", 
            "date": "Date", 
            "sender": "Sender", 
            "receiver": "Recipient",
            "subject": "Subject", 
            "keywords": "Keywords"
        }
        header_row = [column_labels.get(col, col.capitalize()) for col in columns]
        data = [header_row]
        
        # Process emails in batches
        emails_processed = 0
        offset = 0
        
        while emails_processed < total_count:
            # Build query with selected columns and parameterized pagination
            selected_cols = ", ".join(columns + ([body_column] if body_column and include_details else []))
            
            # Handle date formatting in SQL for better performance
            query = f"""
                SELECT {selected_cols}
                FROM emails
                ORDER BY {sort_by}
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, (batch_size, offset))
            batch = cursor.fetchall()
            
            if not batch:
                break
                
            # Process each row for the summary table
            for row in batch:
                values = list(row)
                processed_row = []
                
                # Format each column appropriately
                for i, col in enumerate(columns):
                    value = values[i]
                    
                    if col == "message_id" and value:
                        # Truncate message_id for display
                        processed_row.append(value[:10])
                    elif col == "date" and value:
                        # Format date
                        try:
                            date_obj = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime("%b %d, %Y\n%H:%M:%S")
                            processed_row.append(formatted_date)
                        except (ValueError, TypeError):
                            processed_row.append(str(value))
                    elif col in ("sender", "subject", "receiver"):
                        # Use Paragraph for text that might need wrapping
                        processed_row.append(Paragraph(str(value or ""), styles['TableCell']))
                    else:
                        processed_row.append(str(value or ""))
                        
                data.append(processed_row)
            
            emails_processed += len(batch)
            offset += batch_size
            
            # Print progress info
            progress = min(100, (emails_processed / total_count) * 100)
            print(f"Processed {emails_processed}/{total_count} emails for summary table ({progress:.1f}%)")
        
        # Calculate column widths based on selected columns
        width_map = {
            "message_id": 0.15, 
            "date": 0.2, 
            "sender": 0.25,
            "receiver": 0.2,
            "subject": 0.45, 
            "keywords": 0.2
        }
        
        # Default to 0.2 for any unspecified column
        column_widths = [width_map.get(col, 0.2) * doc.width for col in columns]
        
        # Create and style the table
        table = Table(data, repeatRows=1, colWidths=column_widths)
        
        # Apply table styles
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        
        # Second section: Detailed email contents (optional)
        if include_details:
            elements.append(PageBreak())
            elements.append(Paragraph("Email Contents", styles["Heading1"]))
            elements.append(Spacer(1, 12))
            
            # Process detailed content in batches
            emails_processed = 0
            offset = 0
            
            print(f"Generating detailed content for up to {max_emails} emails...")
            
            while emails_processed < min(total_count, max_emails):
                # Query for detailed content
                if body_column:
                    query = f"""
                        SELECT message_id, 
                               datetime(date) as formatted_date, 
                               sender, 
                               subject,
                               {body_column}
                        FROM emails
                        ORDER BY {sort_by}
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (batch_size, offset))
                else:
                    query = """
                        SELECT message_id, 
                               datetime(date) as formatted_date, 
                               sender, 
                               subject
                        FROM emails
                        ORDER BY {sort_by}
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (batch_size, offset))
                    
                batch = cursor.fetchall()
                
                if not batch:
                    break
                    
                # Process each email's detailed content
                for i, row in enumerate(batch):
                    if emails_processed >= max_emails:
                        break
                        
                    # Extract data from row
                    if body_column:
                        message_id, date_str, sender, subject, body_content = row
                    else:
                        message_id, date_str, sender, subject = row
                        body_content = "(Body not available in database)"
                    
                    # Format date
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime("%b %d, %Y at %H:%M:%S")
                    except (ValueError, TypeError):
                        formatted_date = date_str
                    
                    # Add email header to PDF
                    elements.append(Paragraph(f"Email #{emails_processed+i+1}: {subject}", styles["Heading2"]))
                    elements.append(Paragraph(f"From: {sender}", styles["Normal"]))
                    elements.append(Paragraph(f"Date: {formatted_date}", styles["Normal"]))
                    elements.append(Paragraph(f"ID: {message_id}", styles["Normal"]))
                    elements.append(Spacer(1, 10))
                    
                    # Process and add email body content
                    if body_content and body_content != "(Body not available in database)":
                        try:
                            # Use cache to avoid re-processing the same content
                            if message_id not in cleaned_cache:
                                cleaned_cache[message_id] = cleaner.clean(body_content)
                                
                            cleaned_body = cleaned_cache[message_id]
                            body_text = Paragraph(cleaned_body, styles["EmailBody"])
                            elements.append(body_text)
                        except Exception as e:
                            logger.error(f"Error formatting email body #{emails_processed+i+1}: {e}")
                            elements.append(Paragraph(f"Error processing email body: {str(e)}", styles["Italic"]))
                            elements.append(Paragraph(body_content[:500] + "...", styles["Normal"]))
                    else:
                        elements.append(Paragraph("(No message body)", styles["Italic"]))
                    
                    elements.append(Spacer(1, 12))
                    
                    # Add separator between emails (except after last one)
                    if (emails_processed + i + 1) < min(total_count, max_emails) and i < len(batch) - 1:
                        elements.append(Paragraph("_" * 80, styles["Normal"]))
                        elements.append(Spacer(1, 12))
                        
                        # Add page break every 3 emails for better readability
                        if (emails_processed + i + 1) % 3 == 0:
                            elements.append(PageBreak())
                
                emails_processed += len(batch)
                offset += batch_size
                
                # Print progress info
                progress = min(100, (emails_processed / min(total_count, max_emails)) * 100)
                print(f"Processed {emails_processed}/{min(total_count, max_emails)} emails for detailed content ({progress:.1f}%)")
                
                # Clean up the cache periodically to manage memory
                if len(cleaned_cache) > batch_size * 2:
                    # Keep only the most recent entries
                    keys_to_keep = list(cleaned_cache.keys())[-batch_size:]
                    cleaned_cache = {k: cleaned_cache[k] for k in keys_to_keep}
            
            # Add note if limited by max_emails setting
            if total_count > max_emails:
                elements.append(Paragraph(f"Note: Only showing the first {max_emails} emails. " +
                                         f"Total emails available: {total_count}.", styles["Italic"]))
        
        # Clean up resources
        conn.close()
        cleaned_cache.clear()
        
        # Add footer with version and timestamp
        elements.append(Spacer(1, 24))
        footer = Paragraph(f"Generated by Stone Email System v{config.VERSION} on {current_date}", 
                          styles["Italic"])
        elements.append(footer)
        
        # Build the PDF
        print("Building PDF document...")
        doc.build(elements)
        
        # Report generation time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"PDF report generated: {output_file} ({duration:.1f} seconds)")
        print(f"PDF report successfully generated to {output_file} in {duration:.1f} seconds")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        print(f"Database error: {e}")
        return
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        print(f"Error generating PDF: {e}")
        raise

def generate_thread_report(output_file: str = "thread_report.pdf", 
                         cleaning_options=None,
                         batch_size: int = 100,
                         max_threads: int = 50):
    """
    Generates a PDF report of email threads/conversations.
    
    Args:
        output_file: Path to the output PDF file
        cleaning_options: Dict of text cleaning options
        batch_size: Number of threads to process in each batch
        max_threads: Maximum number of threads to include
    """
    print(f"Starting to generate thread report to {output_file}...")
    start_time = datetime.now()
    
    # Initialize text cleaner
    cleaner = TextCleaner(cleaning_options)
    
    try:
        conn = sqlite3.connect(config.DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check if thread support is available
        cursor.execute("PRAGMA table_info(emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'thread_id' not in columns:
            print("Thread support not available in database. Run 'update_database_schema' first.")
            return
            
        # Check if thread metadata table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_threads'")
        if not cursor.fetchone():
            print("Thread metadata table not found. Run 'update_database_schema' first.")
            return
        
        # Get thread counts
        cursor.execute("""
            SELECT COUNT(DISTINCT thread_id) FROM emails WHERE thread_id IS NOT NULL
        """)
        total_threads = cursor.fetchone()[0] or 0
        
        if total_threads == 0:
            print("No email threads found in the database.")
            return
            
        print(f"Found {total_threads} email threads to process.")
        
        # Set up PDF document
        doc = SimpleDocTemplate(
            output_file,
            pagesize=A4,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            compress=True
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Add title and metadata
        elements.append(Paragraph("Email Thread Report", styles["Title"]))
        elements.append(Spacer(1, 12))
        
        current_date = datetime.now().strftime("%b %d, %Y at %H:%M:%S")
        elements.append(Paragraph(f"Report generated on: {current_date}", styles["Normal"]))
        elements.append(Paragraph(f"Total threads: {total_threads}", styles["Normal"]))
        elements.append(Spacer(1, 24))
        
        # Query threads with metadata
        cursor.execute("""
            SELECT thread_id, subject, participants, start_date, last_update, message_count
            FROM email_threads
            ORDER BY last_update DESC
            LIMIT ?
        """, (max_threads,))
        
        threads = cursor.fetchall()
        
        # Process each thread
        for i, (thread_id, subject, participants, start_date, last_update, message_count) in enumerate(threads):
            # Thread header
            elements.append(Paragraph(f"Thread #{i+1}: {subject}", styles["Heading1"]))
            elements.append(Paragraph(f"Participants: {participants}", styles["Normal"]))
            elements.append(Paragraph(f"Started: {start_date} | Last update: {last_update}", styles["Normal"]))
            elements.append(Paragraph(f"Messages: {message_count}", styles["Normal"]))
            elements.append(Spacer(1, 12))
            
            # Get emails in this thread
            cursor.execute("""
                SELECT message_id, date, sender, subject, content
                FROM emails
                WHERE thread_id = ?
                ORDER BY date ASC
            """, (thread_id,))
            
            thread_emails = cursor.fetchall()
            
            # Process each email in the thread
            for j, (message_id, date_str, sender, email_subject, content) in enumerate(thread_emails):
                elements.append(Paragraph(f"Message #{j+1}", styles["Heading2"]))
                elements.append(Paragraph(f"From: {sender}", styles["Normal"]))
                elements.append(Paragraph(f"Date: {date_str}", styles["Normal"]))
                elements.append(Paragraph(f"Subject: {email_subject}", styles["Normal"]))
                elements.append(Spacer(1, 6))
                
                # Clean and add content
                if content:
                    cleaned_content = cleaner.clean(content)
                    elements.append(Paragraph(cleaned_content, styles["Normal"]))
                else:
                    elements.append(Paragraph("(No content)", styles["Italic"]))
                    
                elements.append(Spacer(1, 12))
                
                # Add separator between emails
                if j < len(thread_emails) - 1:
                    elements.append(Paragraph("-" * 40, styles["Normal"]))
                    elements.append(Spacer(1, 12))
            
            # Add page break after each thread
            elements.append(PageBreak())
        
        # Build PDF
        doc.build(elements)
        
        # Report completion
        duration = (datetime.now() - start_time).total_seconds()
        print(f"Thread report generated: {output_file} in {duration:.1f} seconds")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error generating thread report: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PDF report from email database")
    parser.add_argument("--output", "-o", help="Output PDF file path", default="email_report.pdf")
    parser.add_argument("--batch-size", type=int, help="Batch size for processing", default=100)
    parser.add_argument("--max-emails", type=int, help="Maximum emails to include in detail", default=100)
    parser.add_argument("--summary-only", action="store_true", help="Generate summary table only")
    parser.add_argument("--no-compress", action="store_true", help="Disable PDF compression")
    parser.add_argument("--sort-by", help="Column to sort by (e.g., 'date DESC')", default="date DESC")
    parser.add_argument("--columns", help="Columns to include in summary (comma-separated)", 
                      default="message_id,date,sender,subject")
    
    args = parser.parse_args()
    
    # Parse columns
    columns = [col.strip() for col in args.columns.split(",")]
    
    # Configure cleaning options
    cleaning_options = {
        'strip_html': True,
        'normalize_whitespace': True,
        'handle_urls': True,
        'format_quotes': True,
        'remove_signatures': True,
        'format_sender_changes': True,
        'max_length': 20000,
    }
    
    # Generate the report with provided options
    generate_pdf_report(
        output_file=args.output,
        cleaning_options=cleaning_options,
        batch_size=args.batch_size,
        max_emails=args.max_emails,
        include_details=not args.summary_only,
        compress=not args.no_compress,
        columns=columns,
        sort_by=args.sort_by
    )