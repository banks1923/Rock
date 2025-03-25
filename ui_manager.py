import os
import sys
import logging
import webbrowser
import threading
import json
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import config
import sqlite3
import urllib.parse
import pandas as pd
from flask import jsonify, send_file, request
import tempfile
from datetime import datetime

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

# New helper: Generate report from the database with enhanced diagnostics
def generate_report():
    """Generate report from the database with enhanced diagnostics."""
    report = {}
    
    try:
        # First check if database file exists
        if not os.path.exists(config.DATABASE_FILE):
            report['error'] = f"Database file not found at: {config.DATABASE_FILE}"
            report['status'] = "error"
            return report
            
        with sqlite3.connect(config.DATABASE_FILE) as conn:
            # Test if tables exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
            if not cursor.fetchone():
                report['error'] = "Database exists but contains no emails table"
                report['status'] = "error"
                return report
                
            # Get email counts
            cursor.execute("SELECT COUNT(*) FROM emails")
            count_emails = cursor.fetchone()[0]
            report['emails_count'] = count_emails
            
            # Get thread counts if table exists
            try:
                cursor.execute("SELECT COUNT(*) FROM email_threads")
                count_threads = cursor.fetchone()[0]
                report['threads_count'] = count_threads
            except sqlite3.OperationalError:
                report['threads_count'] = 0
                
            # Get some sample data if available
            if count_emails > 0:
                try:
                    cursor.execute("SELECT date, sender, subject FROM emails ORDER BY date DESC LIMIT 5")
                    recent_emails = cursor.fetchall()
                    report['recent_emails'] = [{"date": row[0], "sender": row[1], "subject": row[2]} 
                                             for row in recent_emails]
                except:
                    pass
                
            if count_emails == 0:
                report['message'] = "No reports available. No emails have been processed."
                report['status'] = "empty"
                
                # Check the data directory for mbox files
                data_dir = Path(config.MBOX_DIRECTORY)
                if data_dir.exists():
                    mbox_files = list(data_dir.glob('*.mbox')) + list(data_dir.glob('*.MBOX'))
                    if mbox_files:
                        report['help'] = f"Found {len(mbox_files)} mbox files in data directory. Run the processor to import them."
                    else:
                        report['help'] = "No mbox files found in data directory. Add .mbox files to the data directory."
                else:
                    report['help'] = f"Data directory '{config.MBOX_DIRECTORY}' not found."
            else:
                report['status'] = "success"
                
    except Exception as e:
        report['error'] = f"Error generating report: {str(e)}"
        report['status'] = "error"
        import traceback
        report['traceback'] = traceback.format_exc()
        
    return report

# New helper: Execute a SQL query with better error handling
def run_query(sql_query):
    """Execute a SQL query with better error handling."""
    results = []
    
    if not sql_query.strip():
        return [{"error": "Empty query provided"}]
        
    try:
        # First check if database exists
        if not os.path.exists(config.DATABASE_FILE):
            return [{"error": f"Database file not found at: {config.DATABASE_FILE}"}]
            
        # Very basic SQL injection protection
        sql_lower = sql_query.lower().strip()
        if not sql_lower.startswith('select'):
            return [{"error": "Only SELECT queries are allowed"}]
            
        # Block potentially dangerous queries
        for banned in ['delete', 'drop', 'insert', 'update', 'pragma', 'attach']:
            if banned in sql_lower:
                return [{"error": f"Query contains forbidden keyword: {banned}"}]
        
        with sqlite3.connect(config.DATABASE_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql_query)
            
            # Limit large result sets for performance
            raw_results = cursor.fetchmany(1000)  # Limit to 1000 rows max
            
            if not raw_results:
                return [{"info": "Query executed successfully but returned no results"}]
                
            # Process the results
            column_names = [desc[0] for desc in cursor.description]
            results = []
            
            for row in raw_results:
                result_dict = {}
                for i, value in enumerate(row):
                    column = column_names[i]
                    result_dict[column] = value
                results.append(result_dict)
                
            # Add a message if results were limited
            if len(raw_results) == 1000:
                results.append({"note": "Results limited to 1000 rows"})
                
    except Exception as e:
        results = [{"error": str(e)}]
        
    return results

class CustomHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving the UI and API endpoints."""
    
    # Introduce a class-level cache for static files
    _file_cache = {}

    def __init__(self, *args, metrics=None, **kwargs):
        self.metrics = metrics or {}
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        # Silence the default logging to avoid cluttering the console
        return
    
    def do_GET(self):
        """Handle GET requests."""
        # New endpoint for report generation
        if self.path.startswith('/api/report'):
            report = generate_report()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(report).encode())
            return

        # New endpoint for query execution (only SELECT queries allowed)
        if self.path.startswith('/api/query'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get('q', [''])[0]
            # Very basic check to allow only SELECT queries
            if not query.lower().strip().startswith("select"):
                result = {"error": "Only SELECT queries are allowed."}
            else:
                result = run_query(query)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return

        if self.path == '/api/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.metrics).encode())
            return
            
        # Serve static files from ui_static directory
        if self.path == '/':
            self.path = '/index.html'
            
        try:
            ui_dir = Path(__file__).parent / 'ui_static'
            file_path = ui_dir / self.path.lstrip('/')
            cache_key = str(file_path)

            if cache_key in CustomHandler._file_cache:
                file_content, content_type = CustomHandler._file_cache[cache_key]
            else:
                if not file_path.is_file():
                    self.send_error(404, "File not found")
                    return
                # Determine content type by file extension
                if self.path.endswith('.html'):
                    content_type = 'text/html'
                elif self.path.endswith('.css'):
                    content_type = 'text/css'
                elif self.path.endswith('.js'):
                    content_type = 'text/javascript'
                elif self.path.endswith('.json'):
                    content_type = 'application/json'
                else:
                    content_type = 'application/octet-stream'
                with open(file_path, 'rb') as file:
                    file_content = file.read()
                # Cache the file content
                CustomHandler._file_cache[cache_key] = (file_content, content_type)

            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(file_content)
        except Exception as e:
            self.send_error(500, str(e))

def create_basic_ui_files():
    """Create basic UI files if they don't exist."""
    # Check for both "ui_static" and "UI Static" directories
    ui_dir = Path(__file__).parent / 'ui_static'
    alt_ui_dir = Path(__file__).parent / 'UI Static'
    
    # Use whichever one exists, or create ui_static if neither exists
    if alt_ui_dir.exists():
        ui_dir = alt_ui_dir
    else:
        ui_dir.mkdir(exist_ok=True)
    
    # Create index.html if it doesn't exist
    index_path = ui_dir / 'index.html'
    if not index_path.exists():
        with open(index_path, 'w') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Stone Email & Image Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            width: 80%;
            margin: auto;
            overflow: auto;
            padding: 20px;
            background: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        header {
            background: #333;
            color: white;
            padding: 10px 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
            margin-bottom: 20px;
        }
        h1, h2, h3 {
            color: #333;
        }
        .card {
            background: #f9f9f9;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 5px solid #333;
        }
        .warning {
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        table, th, td {
            border: 1px solid #ddd;
            padding: 8px;
        }
        th {
            background-color: #f2f2f2;
            text-align: left;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .instructions {
            background-color: #e7f3fe;
            border-left: 6px solid #2196F3;
            padding: 10px;
            margin: 15px 0;
        }
        .query-section { margin-top: 20px; }
        .query-section input[type="text"] { width: 70%; padding: 8px; }
        .query-section button { padding: 8px 12px; }
        .error { color: #d9534f; background-color: #f2dede; padding: 10px; border-radius: 4px; }
        .success { color: #5cb85c; background-color: #dff0d8; padding: 10px; border-radius: 4px; }
        pre { white-space: pre-wrap; overflow-x: auto; }
        .results-table { margin-top: 15px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Stone Email & Image Processor</h1>
        </header>
        
        <div class="instructions">
            <h3>How to Use This Tool</h3>
            <p>To process files, place them in the input directory (default: <code>data</code> folder) and run the application.</p>
            <p>Supported file types:</p>
            <ul>
                <li><strong>Emails:</strong> .mbox, .eml files</li>
                <li><strong>Images:</strong> .jpg, .jpeg, .png files</li>
                <li><strong>Documents:</strong> .pdf files</li>
            </ul>
            <p>You can specify a different input directory with the <code>--directory</code> or <code>-d</code> command-line option.</p>
        </div>
        
        <div class="card">
            <h2>Processing Summary</h2>
            <div id="processing-summary">Loading...</div>
        </div>
        
        <div id="unsupported-files-section" style="display: none;" class="card warning">
            <h2>Unsupported Files</h2>
            <div id="unsupported-files">Loading...</div>
        </div>
        
        <div class="card">
            <h2>Recent Processing Details</h2>
            <div id="processing-details">Loading...</div>
        </div>

        <div id="query-section" class="query-section">
            <h2>Run Query</h2>
            <input type="text" id="query-input" placeholder="Enter SELECT query (e.g., SELECT * FROM emails LIMIT 10)">
            <button onclick="runQuery()">Run Query</button>
            <div id="query-results"></div>
        </div>
        
        <div id="report-section" class="query-section">
            <h2>Generate Report</h2>
            <button onclick="generateReport()">Generate Report</button>
            <div id="report-results"></div>
        </div>
    </div>
    <script>
        // Fetch processing metrics from the server
        async function fetchMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                displayMetrics(data);
            } catch (error) {
                console.error('Error fetching metrics:', error);
                document.getElementById('processing-summary').innerHTML = 
                    '<p>Error loading metrics. Please try refreshing the page.</p>';
            }
        }
        
        function displayMetrics(metrics) {
            // Display summary
            let summaryHtml = '<table>';
            
            if (metrics.start_time) {
                const startTime = new Date(metrics.start_time * 1000);
                const elapsedTime = ((Date.now() / 1000) - metrics.start_time).toFixed(2);
                summaryHtml += `<tr><td><strong>Processing Start Time</strong></td><td>${startTime.toLocaleString()}</td></tr>`;
                summaryHtml += `<tr><td><strong>Total Processing Time</strong></td><td>${elapsedTime} seconds</td></tr>`;
            }
            
            if ('processed_emails' in metrics) {
                summaryHtml += `<tr><td><strong>Processed Emails</strong></td><td>${metrics.processed_emails}</td></tr>`;
            }
            
            if ('processed_files' in metrics) {
                summaryHtml += `<tr><td><strong>Processed Email Files</strong></td><td>${metrics.processed_files}</td></tr>`;
            }
            
            if ('processed_images' in metrics) {
                summaryHtml += `<tr><td><strong>Processed Images</strong></td><td>${metrics.processed_images}</td></tr>`;
            }
            
            if ('image_files_found' in metrics) {
                summaryHtml += `<tr><td><strong>Image Files Found</strong></td><td>${metrics.image_files_found}</td></tr>`;
            }
            
            if ('processed_pdfs' in metrics) {
                summaryHtml += `<tr><td><strong>Processed PDFs</strong></td><td>${metrics.processed_pdfs}</td></tr>`;
            }
            
            if ('pdf_files_found' in metrics) {
                summaryHtml += `<tr><td><strong>PDF Files Found</strong></td><td>${metrics.pdf_files_found}</td></tr>`;
            }
            
            summaryHtml += '</table>';
            document.getElementById('processing-summary').innerHTML = summaryHtml;
            
            // Display unsupported files if present
            if (metrics.unsupported_files && metrics.unsupported_files.length > 0) {
                document.getElementById('unsupported-files-section').style.display = 'block';
                
                // Group by extension
                const byExtension = {};
                metrics.unsupported_files.forEach(file => {
                    const ext = file.extension || 'no extension';
                    if (!byExtension[ext]) {
                        byExtension[ext] = [];
                    }
                    byExtension[ext].push(file);
                });
                
                let unsupportedHtml = `<p>Found ${metrics.unsupported_files.length} files with unsupported file types:</p>`;
                unsupportedHtml += '<table>';
                unsupportedHtml += '<tr><th>Extension</th><th>Count</th><th>Examples</th></tr>';
                
                for (const ext in byExtension) {
                    const files = byExtension[ext];
                    const examples = files.slice(0, 3).map(f => f.name).join(', ');
                    const moreCount = files.length > 3 ? ` and ${files.length - 3} more` : '';
                    
                    unsupportedHtml += `<tr>
                        <td>${ext}</td>
                        <td>${files.length}</td>
                        <td>${examples}${moreCount}</td>
                    </tr>`;
                }
                
                unsupportedHtml += '</table>';
                unsupportedHtml += '<p>To process these files, support for these file types needs to be added to the application.</p>';
                
                document.getElementById('unsupported-files').innerHTML = unsupportedHtml;
            } else {
                document.getElementById('unsupported-files-section').style.display = 'none';
            }
            
            // Display additional details if available
            let detailsHtml = '<p>No detailed information available.</p>';
            document.getElementById('processing-details').innerHTML = detailsHtml;
        }
        
        async function generateReport() {
            try {
                document.getElementById('report-results').innerHTML = '<p>Loading report data...</p>';
                const response = await fetch('/api/report');
                const report = await response.json();
                
                let reportHtml = '';
                
                if (report.status === 'error') {
                    reportHtml = `<div class="error"><strong>Error:</strong> ${report.error}</div>`;
                    if (report.traceback) {
                        reportHtml += `<pre>${report.traceback}</pre>`;
                    }
                } else if (report.status === 'empty') {
                    reportHtml = `<div class="error">
                        <p>${report.message}</p>
                        <p>${report.help || 'Add .mbox files to your data directory and run the processor.'}</p>
                    </div>`;
                } else {
                    reportHtml = `<div class="success">
                        <h3>Database Summary</h3>
                        <table>
                            <tr><td>Total Emails:</td><td>${report.emails_count}</td></tr>
                            <tr><td>Total Threads:</td><td>${report.threads_count}</td></tr>
                        </table>`;
                        
                    if (report.recent_emails && report.recent_emails.length > 0) {
                        reportHtml += `<h3>Recent Emails</h3>
                        <table>
                            <tr><th>Date</th><th>Sender</th><th>Subject</th></tr>`;
                        
                        report.recent_emails.forEach(email => {
                            reportHtml += `<tr>
                                <td>${email.date}</td>
                                <td>${email.sender}</td>
                                <td>${email.subject}</td>
                            </tr>`;
                        });
                        
                        reportHtml += `</table>`;
                    }
                    
                    reportHtml += `</div>`;
                }
                
                document.getElementById('report-results').innerHTML = reportHtml;
            } catch (error) {
                document.getElementById('report-results').innerHTML = 
                    `<div class="error">Error generating report: ${error.message}</div>`;
            }
        }
        
        async function runQuery() {
            const q = document.getElementById('query-input').value.trim();
            
            if (!q) {
                document.getElementById('query-results').innerHTML = 
                    `<div class="error">Please enter a SQL query</div>`;
                return;
            }
            
            try {
                document.getElementById('query-results').innerHTML = '<p>Executing query...</p>';
                const response = await fetch('/api/query?q=' + encodeURIComponent(q));
                const result = await response.json();
                
                if (result.length === 0) {
                    document.getElementById('query-results').innerHTML = 
                        '<p>Query returned no results.</p>';
                    return;
                }
                
                if (result[0].error) {
                    document.getElementById('query-results').innerHTML = 
                        `<div class="error">Error: ${result[0].error}</div>`;
                    return;
                }
                
                if (result[0].info) {
                    document.getElementById('query-results').innerHTML = 
                        `<div class="info">${result[0].info}</div>`;
                    return;
                }
                
                // Display results as a table
                let tableHtml = '<div class="results-table"><table><tr>';
                
                // Get all possible column names from all objects
                const columns = new Set();
                result.forEach(row => {
                    if (!row.note) {  // Skip the "note" row
                        Object.keys(row).forEach(key => columns.add(key));
                    }
                });
                
                // Create header row
                columns.forEach(col => {
                    tableHtml += `<th>${col}</th>`;
                });
                tableHtml += '</tr>';
                
                // Add data rows
                result.forEach(row => {
                    if (row.note) {
                        // This is our note about limit, don't include in table
                        return;
                    }
                    
                    tableHtml += '<tr>';
                    columns.forEach(col => {
                        tableHtml += `<td>${row[col] !== undefined ? row[col] : ''}</td>`;
                    });
                    tableHtml += '</tr>';
                });
                
                tableHtml += '</table></div>';
                
                // Add note if present
                const noteRow = result.find(row => row.note);
                if (noteRow) {
                    tableHtml += `<p><em>${noteRow.note}</em></p>`;
                }
                
                document.getElementById('query-results').innerHTML = tableHtml;
            } catch (error) {
                document.getElementById('query-results').innerHTML = 
                    `<div class="error">Error running query: ${error.message}</div>`;
            }
        }
        
        // Add example queries for easy use
        function setExampleQuery(queryType) {
            const queryInput = document.getElementById('query-input');
            switch(queryType) {
                case 'allEmails':
                    queryInput.value = "SELECT * FROM emails LIMIT 10";
                    break;
                case 'emailCount':
                    queryInput.value = "SELECT COUNT(*) AS email_count FROM emails";
                    break;
                case 'threadCount': 
                    queryInput.value = "SELECT thread_id, COUNT(*) AS message_count FROM emails GROUP BY thread_id ORDER BY message_count DESC LIMIT 10";
                    break;
                case 'senders':
                    queryInput.value = "SELECT sender, COUNT(*) AS email_count FROM emails GROUP BY sender ORDER BY email_count DESC LIMIT 10";
                    break;
                case 'dateRange':
                    queryInput.value = "SELECT date, subject, sender FROM emails ORDER BY date DESC LIMIT 20";
                    break;
            }
            runQuery();
        }
        
        // Initial fetch
        fetchMetrics();
        
        // Refresh every 5 seconds
        setInterval(fetchMetrics, 5000);
    </script>
</body>
</html>''')
    
    # Create an empty style.css file
    css_path = ui_dir / 'style.css'
    if not css_path.exists():
        with open(css_path, 'w') as f:
            f.write('/* Additional styles can be placed here */')

def start_ui_server(metrics, logger, db_path=None):
    """
    Start the Flask UI server.
    
    Args:
        metrics: Dictionary containing processing metrics
        logger: Application logger
        db_path: Path to the SQLite database file
    
    Returns:
        tuple: (server, server_thread)
    """
    from flask import Flask, render_template, jsonify, request
    import threading
    import webbrowser
    import socket
    
    # Create the Flask app
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Fix for NameError: Make app available to other functions
    global flask_app
    flask_app = app
    
    # Check for both "ui_static" and "UI Static" directories
    ui_dir = Path(__file__).parent / 'ui_static'
    alt_ui_dir = Path(__file__).parent / 'UI Static'
    
    if alt_ui_dir.exists():
        ui_dir = alt_ui_dir
    
    # Create UI files if they don't exist
    create_basic_ui_files()
    
    # Create a handler class with metrics argument
    handler = lambda *args, **kwargs: CustomHandler(*args, metrics=metrics, **kwargs)
    
    # Create and start the server
    server = ThreadingHTTPServer((config.UI_HOST, config.UI_PORT), handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    logger.info(f"UI server started at http://{config.UI_HOST}:{config.UI_PORT}")
    
    # Add database query endpoints
    @app.route('/api/query', methods=['POST'])
    def query_database():
        if not db_path:
            return jsonify({"error": "Database path not configured"}), 500
            
        try:
            query = request.json.get('query')
            if not query:
                return jsonify({"error": "No query provided"}), 400
                
            # Limit to SELECT queries for safety
            if not query.strip().lower().startswith('select'):
                return jsonify({"error": "Only SELECT queries are allowed"}), 403
                
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return jsonify(df.to_dict(orient='records'))
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/tables', methods=['GET'])
    def get_tables():
        if not db_path:
            return jsonify({"error": "Database path not configured"}), 500
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return jsonify({"tables": tables})
        except Exception as e:
            logger.error(f"Error fetching tables: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/report', methods=['GET'])
    def generate_report():
        if not db_path:
            return jsonify({"error": "Database path not configured"}), 500
            
        try:
            report_type = request.args.get('type', 'full')
            format_type = request.args.get('format', 'csv')
            
            conn = sqlite3.connect(db_path)
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_report_{timestamp}.{format_type}"
            filepath = os.path.join(temp_dir, filename)
            
            if report_type == 'emails':
                df = pd.read_sql_query("SELECT * FROM emails", conn)
            elif report_type == 'images':
                df = pd.read_sql_query("SELECT * FROM images", conn)
            elif report_type == 'documents':
                df = pd.read_sql_query("SELECT * FROM documents", conn)
            else:  # full report
                tables = {}
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                
                for table_name in [row[0] for row in cursor.fetchall()]:
                    tables[table_name] = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # For full report, create Excel with multiple sheets
                if format_type == 'xlsx':
                    with pd.ExcelWriter(filepath) as writer:
                        for table_name, df in tables.items():
                            df.to_excel(writer, sheet_name=table_name[:31])  # Excel sheet name length limit
                    conn.close()
                    return send_file(filepath, as_attachment=True, download_name=filename)
                
                # Default to CSV for full report
                df = pd.concat([tables[t] for t in tables], keys=tables.keys())
            
            conn.close()
            
            # Export based on format
            if format_type == 'csv':
                df.to_csv(filepath, index=False)
            elif format_type == 'xlsx':
                df.to_excel(filepath, index=False)
            elif format_type == 'json':
                df.to_json(filepath, orient='records')
            else:
                return jsonify({"error": "Unsupported format"}), 400
            
            return send_file(filepath, as_attachment=True, download_name=filename)
            
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Add search endpoint
    @app.route('/api/search', methods=['POST'])
    def search_database():
        if not db_path:
            return jsonify({"error": "Database path not configured"}), 500
            
        try:
            search_term = request.json.get('term')
            tables = request.json.get('tables', ['emails'])
            
            if not search_term:
                return jsonify({"error": "No search term provided"}), 400
                
            conn = sqlite3.connect(db_path)
            results = {}
            
            for table in tables:
                try:
                    # Get table columns
                    cursor = conn.cursor()
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Build search query for text columns
                    search_conditions = " OR ".join([f"{col} LIKE ?" for col in columns])
                    search_params = [f"%{search_term}%"] * len(columns)
                    
                    query = f"SELECT * FROM {table} WHERE {search_conditions} LIMIT 1000"
                    df = pd.read_sql_query(query, conn, params=search_params)
                    results[table] = df.to_dict(orient='records')
                except Exception as e:
                    results[table] = {"error": str(e)}
            
            conn.close()
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/search', methods=['GET', 'POST'])
    def search_database():
        """API endpoint to search the database for emails"""
        try:
            # Get search parameters
            if request.method == 'POST':
                data = request.json
                keyword = data.get('keyword', '')
                field = data.get('field', 'all')  # 'subject', 'content', 'sender', 'all'
                limit = int(data.get('limit', 100))
            else:  # GET method
                keyword = request.args.get('keyword', '')
                field = request.args.get('field', 'all')
                limit = int(request.args.get('limit', 100))
            
            # Connect to database
            conn = sqlite3.connect(config.DATABASE_FILE)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Build the query based on which field to search
            if field == 'subject':
                query = "SELECT * FROM emails WHERE subject LIKE ? LIMIT ?"
                params = (f'%{keyword}%', limit)
            elif field == 'content':
                query = "SELECT * FROM emails WHERE content LIKE ? LIMIT ?"
                params = (f'%{keyword}%', limit)
            elif field == 'sender':
                query = "SELECT * FROM emails WHERE sender LIKE ? LIMIT ?"
                params = (f'%{keyword}%', limit)
            else:  # 'all' - search all fields
                query = "SELECT * FROM emails WHERE subject LIKE ? OR content LIKE ? OR sender LIKE ? LIMIT ?"
                params = (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit)
            
            # Execute search
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return jsonify({
                'success': True,
                'count': len(results),
                'results': results
            })
            
        except Exception as e:
            logger.exception(f"Search error: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return server, server_thread

def open_ui_in_browser(logger):
    """Open the UI in the default web browser."""
    url = f"http://{config.UI_HOST}:{config.UI_PORT}"
    
    try:
        if config.BROWSER_PATH:
            browser = webbrowser.get(config.BROWSER_PATH)
            browser.open_new_tab(url)
        else:
            webbrowser.open_new_tab(url)
        logger.info(f"Opened UI in browser: {url}")
        return True
    except Exception as e:
        logger.error(f"Failed to open UI in browser: {e}")
        logger.info(f"UI is available at: {url}")
        return False
