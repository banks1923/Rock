import os
from flask import Flask, render_template, request, url_for, redirect, make_response
from read_db import read_database
import config
import datetime

app = Flask(__name__)

# Ensure template directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)

@app.route('/')
def index():
    # Get query parameters
    query = request.args.get('query', '')
    page = max(1, int(request.args.get('page', 1)))
    limit = int(request.args.get('limit', 20))
    order_by = request.args.get('order_by', 'date DESC')
    count_only = request.args.get('count_only') == 'true'
    
    # Available page size options
    page_sizes = [10, 20, 50, 100]
    
    # Calculate offset based on page
    offset = (page - 1) * limit
    
    # Query database
    result = read_database(config.DATABASE_FILE, limit, offset, query, order_by)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1, 'has_next': False, 'has_prev': False}
    
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
    
    # For reports, we want all matching emails (no pagination)
    result = read_database(config.DATABASE_FILE, None, 0, query, order_by)
    
    if not result:
        result = {'emails': [], 'total_count': 0, 'page': 1, 'total_pages': 1}
    
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
            writer.writerow([
                email.get('date', ''),
                email.get('sender', ''),
                email.get('receiver', ''),
                email.get('subject', ''),
                email.get('content', '')
            ])
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    
    else:  # Default to text format
        # Generate plain text report
        lines = [
            f"Email Report {'for query: '+query if query else '(All Emails)'}",
            f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total emails: {result['total_count']}",
            "-" * 80
        ]
        
        for email in result['emails']:
            lines.extend([
                f"Date: {email.get('date', '')}",
                f"From: {email.get('sender', '')}",
                f"To: {email.get('receiver', '')}",
                f"Subject: {email.get('subject', '')}",
                f"Content:",
                email.get('content', ''),
                "-" * 80
            ])
        
        response = make_response("\n".join(lines))
        response.headers["Content-Disposition"] = f"attachment; filename=email_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        response.headers["Content-type"] = "text/plain"
        return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
