# Stone Email & Image Processor

A utility for processing email, image, and PDF files.

## Quick Start

1. Place your files in the `data` directory (default location)
2. Run the processor: `python main.py`
3. View results in the automatically opened UI

## Supported File Types

- **Emails**: .mbox, .eml files
- **Images**: .jpg, .jpeg, .png files
- **Documents**: .pdf files

## Custom Input Directory

You can specify a custom directory for input files:

# Stone Email Processor - Database Query Guide

## Running Queries

There are multiple ways to query the Stone Email Processor database:

### Option 1: Using the Web UI

1. Start the application with the default UI:
   ```
   python main.py
   ```

2. Open your web browser to http://localhost:8000 (or configured port)

3. Click on the "Database Query" tab

4. Enter your SQL query in the text box (only SELECT queries are allowed)
   Example: `SELECT * FROM emails WHERE sender LIKE '%@example.com' LIMIT 10`

5. Click "Run Query" to see the results

6. Use the download buttons to export results in CSV, Excel or JSON format

### Option 2: Command-line Query

Run a one-time query and display results in the terminal:

```
python main.py --query "SELECT * FROM emails LIMIT 10"
```

Save query results to a CSV file:

```
python main.py --query "SELECT * FROM emails LIMIT 100" --output results.csv
```

### Option 3: Dedicated Query Tool

The application includes a dedicated query tool that can be used directly:

```
python database_query.py "SELECT * FROM emails LIMIT 10"
```

Save results to a file:

```
python database_query.py "SELECT * FROM emails LIMIT 100" results.csv
```

View database structure:

```
python database_query.py --info
```

## Query Examples

Here are some useful queries to get you started:

```sql
-- Get all emails
SELECT * FROM emails LIMIT 100

-- Count emails by sender
SELECT sender, COUNT(*) AS email_count 
FROM emails 
GROUP BY sender 
ORDER BY email_count DESC 
LIMIT 20

-- Find emails with specific subject
SELECT * FROM emails 
WHERE subject LIKE '%meeting%'
ORDER BY date DESC

-- Show emails in a specific date range
SELECT * FROM emails 
WHERE date BETWEEN '2023-01-01' AND '2023-01-31'
ORDER BY date

-- Find emails from a specific sender
SELECT * FROM emails WHERE sender LIKE '%@example.com'
```

## Installing Required Packages

If you get errors about missing packages, install them using pip:

```
pip install pandas tabulate
