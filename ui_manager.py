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

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

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

def start_ui_server(metrics, logger):
    """
    Start the UI server in a separate thread.
    
    Args:
        metrics: Dictionary containing processing metrics
        logger: Logger instance
        
    Returns:
        tuple: (server, server_thread)
    """
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
