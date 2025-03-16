import os
<<<<<<< HEAD
import html
import json
import mimetypes
from flask import Flask, render_template, request, url_for, redirect, make_response, send_file, jsonify
from read_db import read_database, get_attachment_data, process_attachment_for_ocr
import config
import datetime
from thread_utils import enhance_email_content
=======
from flask import Flask, render_template, request, url_for, redirect, make_response
from read_db import read_database
import config
import datetime
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de

app = Flask(__name__)

# Ensure template directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)

<<<<<<< HEAD
# Define template filter for decoding HTML entities
@app.template_filter('decode_html')
def decode_html(text):
    """Decode HTML entities in text"""
    if text is None:
        return ""
    return html.unescape(text)

=======
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
@app.route('/')
def index():
    # Get query parameters
    query = request.args.get('query', '')
    page = max(1, int(request.args.get('page', 1)))
    limit = int(request.args.get('limit', 20))
    order_by = request.args.get('order_by', 'date DESC')
    count_only = request.args.get('count_only') == 'true'
<<<<<<< HEAD
    include_ocr = request.args.get('include_ocr') == 'true'
=======
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
    
    # Available page size options
    page_sizes = [10, 20, 50, 100]
    
    # Calculate offset based on page
    offset = (page - 1) * limit
    
<<<<<<< HEAD
    # Query database with OCR option
    result = read_database(config.DATABASE_FILE, limit, offset, query, order_by, include_ocr=include_ocr)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1, 'has_next': False, 'has_prev': False}
    else:
        # Process each email to identify thread parts
        result['emails'] = [enhance_email_content(email) for email in result['emails']]
=======
    # Query database
    result = read_database(config.DATABASE_FILE, limit, offset, query, order_by)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1, 'has_next': False, 'has_prev': False}
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
    
    # Available sort options
    sort_options = [
        {'value': 'date DESC', 'label': 'Date (newest first)'},
        {'value': 'date ASC', 'label': 'Date (oldest first)'},
        {'value': 'sender ASC', 'label': 'Sender A-Z'},
        {'value': 'sender DESC', 'label': 'Sender Z-A'},
        {'value': 'subject ASC', 'label': 'Subject A-Z'},
        {'value': 'subject DESC', 'label': 'Subject Z-A'},
        {'value': 'message_id ASC', 'label': 'ID (ascending)'},
        {'value': 'message_id DESC', 'label': 'ID (descending)'}
    ]
    
    # Generate pagination range
    pagination_window = 5  # Number of page links to show
    start_page = max(1, page - pagination_window // 2)
    end_page = min(result['total_pages'], start_page + pagination_window - 1)
    pagination_range = range(start_page, end_page + 1)
    
    return render_template('index.html', 
                          result=result,
                          query=query, 
                          page=page,
                          limit=limit,
                          page_sizes=page_sizes,
                          order_by=order_by,
                          sort_options=sort_options,
                          count_only=count_only,
                          pagination_range=pagination_range)

@app.route('/settings', methods=['POST'])
def settings():
    # Get form data
    query = request.form.get('query', '')
    limit = request.form.get('limit', '20')
    order_by = request.form.get('order_by', 'date DESC')
    count_only = 'count_only' in request.form
    
    # Redirect to index with new settings
    return redirect(url_for('index', 
                           query=query, 
                           limit=limit,
                           order_by=order_by,
                           count_only='true' if count_only else 'false',
                           page=1))  # Reset to first page with new settings

@app.route('/report')
def generate_report():
    # Get query parameters
    query = request.args.get('query', '')
    order_by = request.args.get('order_by', 'date DESC')
<<<<<<< HEAD
    include_ocr = request.args.get('include_ocr') == 'true'
    
    # For reports, we want all matching emails (no pagination)
    result = read_database(config.DATABASE_FILE, None, 0, query, order_by, include_ocr=include_ocr)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1}
    else:
        # Process each email to identify thread parts
        result['emails'] = [enhance_email_content(email) for email in result['emails']]
=======
    
    # For reports, we want all matching emails (no pagination)
    result = read_database(config.DATABASE_FILE, None, 0, query, order_by)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1}
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
    
    # Generate report timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template('report.html',
                          result=result,
                          query=query, 
                          order_by=order_by,
                          timestamp=timestamp,
                          report_title=f"Email Report: {query}" if query else "Complete Email Database Report")

@app.route('/download-report')
def download_report():
    # Get query parameters
    query = request.args.get('query', '')
    order_by = request.args.get('order_by', 'date DESC')
    format_type = request.args.get('format', 'txt')
    
    # For reports, we want all matching emails (no pagination)
    result = read_database(config.DATABASE_FILE, None, 0, query, order_by)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1}
<<<<<<< HEAD
    else:
        # Process each email to identify thread parts for better formatting
        result['emails'] = [enhance_email_content(email) for email in result['emails']]
=======
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
    
    if format_type == 'csv':
        # Generate CSV file
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'From', 'To', 'Subject', 'Content'])
        
        # Write data rows
        for email in result['emails']:
<<<<<<< HEAD
            # Decode HTML entities before writing to CSV
            writer.writerow([
                email.get('date', ''),
                html.unescape(email.get('sender', '')),
                html.unescape(email.get('receiver', '')),
                html.unescape(email.get('subject', '')),
                html.unescape(email.get('content', ''))
=======
            writer.writerow([
                email.get('date', ''),
                email.get('sender', ''),
                email.get('receiver', ''),
                email.get('subject', ''),
                email.get('content', '')
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
            ])
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-type"] = "text/csv"
        return response
<<<<<<< HEAD
    elif format_type == 'json':
        # Generate JSON file
        # Clean data for JSON serialization
        clean_emails = []
        for email in result['emails']:
            clean_email = {
                'date': email.get('date', ''),
                'sender': html.unescape(email.get('sender', '')),
                'receiver': html.unescape(email.get('receiver', '')),
                'subject': html.unescape(email.get('subject', '')),
                'content': html.unescape(email.get('content', ''))
            }
            
            # Include thread parts if available
            if 'thread_parts' in email:
                clean_email['thread_parts'] = [html.unescape(part) for part in email['thread_parts']]
                
            # Include attachment info if available
            if 'attachments' in email and email['attachments']:
                clean_email['attachments'] = email['attachments']
                
            clean_emails.append(clean_email)
            
        json_data = json.dumps({
            'report_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'query': query,
            'total_count': result['total_count'],
            'emails': clean_emails
        }, indent=2)
        
        response = make_response(json_data)
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        response.headers["Content-type"] = "application/json"
        return response
    elif format_type == 'html':
        # Generate a standalone HTML report
        html_content = render_template('report_download.html',
                          result=result,
                          query=query, 
                          order_by=order_by,
                          timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          report_title=f"Email Report: {query}" if query else "Complete Email Database Report")
        
        response = make_response(html_content)
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        response.headers["Content-type"] = "text/html"
        return response
=======
    
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
    else:  # Default to text format
        # Generate plain text report
        lines = [
            f"Email Report {'for query: '+query if query else '(All Emails)'}",
            f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total emails: {result['total_count']}",
            "-" * 80
        ]
        
        for email in result['emails']:
<<<<<<< HEAD
            # Decode HTML entities in text report
            lines.extend([
                f"Date: {email.get('date', '')}",
                f"From: {html.unescape(email.get('sender', ''))}",
                f"To: {html.unescape(email.get('receiver', ''))}",
                f"Subject: {html.unescape(email.get('subject', ''))}",
                f"Content:"
            ])
            
            # If we have thread parts, display them with separators
            if 'thread_parts' in email and email['thread_parts']:
                for i, part in enumerate(email['thread_parts']):
                    if i > 0:  # Add separator between parts
                        lines.append("- - - - - - - - - - - - - - - - - - - -")
                    lines.append(html.unescape(part))
            else:
                lines.append(html.unescape(email.get('content', '')))
                
            lines.append("-" * 80)
=======
            lines.extend([
                f"Date: {email.get('date', '')}",
                f"From: {email.get('sender', '')}",
                f"To: {email.get('receiver', '')}",
                f"Subject: {email.get('subject', '')}",
                f"Content:",
                email.get('content', ''),
                "-" * 80
            ])
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
        
        response = make_response("\n".join(lines))
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        response.headers["Content-type"] = "text/plain"
        return response

<<<<<<< HEAD
@app.route('/attachment/<int:message_id>/<path:filename>')
def download_attachment(message_id, filename):
    """
    Download an email attachment.
    
    Args:
        message_id: The email message ID
        filename: The attachment filename
    """
    try:
        attachment_data = get_attachment_data(config.DATABASE_FILE, message_id, filename)
        
        if not attachment_data:
            return "Attachment not found", 404
            
        content, mime_type = attachment_data
        
        # If mime_type is not provided, try to guess from filename
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'  # Default MIME type
                
        # Create a temporary file to serve
        temp_file = os.path.join(config.TEMP_DIR, f"{message_id}_{filename}")
        os.makedirs(os.path.dirname(temp_file), exist_ok=True)
        
        with open(temp_file, 'wb') as f:
            f.write(content)
            
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
    except Exception as e:
        print(f"Error serving attachment: {e}")
        return "Error retrieving attachment", 500

@app.route('/ocr/<int:attachment_id>')
def ocr_attachment(attachment_id):
    """
    Process an attachment through OCR and return the text.
    
    Args:
        attachment_id: The attachment ID to process
    """
    try:
        # Check if we already have OCR text
        from read_db import get_attachment_text
        ocr_text = get_attachment_text(config.DATABASE_FILE, attachment_id)
        
        # If not, process it
        if not ocr_text:
            ocr_text = process_attachment_for_ocr(config.DATABASE_FILE, attachment_id)
            
        if not ocr_text:
            return jsonify({
                'success': False,
                'error': 'OCR processing failed or unsupported attachment type'
            }), 400
            
        # Return OCR text
        return jsonify({
            'success': True,
            'ocr_text': ocr_text
        })
        
    except Exception as e:
        print(f"Error processing OCR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

=======
>>>>>>> 5dd220e29bd9c42de6ab7acbe763b94e6d7878de
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
