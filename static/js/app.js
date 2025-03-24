// Database query and reporting functionality

document.addEventListener('DOMContentLoaded', function() {
    // Setup tabs for different sections
    setupTabs();
    
    // Load database tables for the query builder
    loadDatabaseTables();
    
    // Set up event listeners
    document.getElementById('runQueryBtn')?.addEventListener('click', runQuery);
    document.getElementById('searchBtn')?.addEventListener('click', searchDatabase);
    
    // Setup report download buttons
    setupReportButtons();
});

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to current button and corresponding content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Activate first tab by default if exists
    if (tabButtons.length > 0) {
        tabButtons[0].click();
    }
}

function loadDatabaseTables() {
    fetch('/api/tables')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            const tablesSelect = document.getElementById('tables-select');
            if (!tablesSelect) return;
            
            // Clear existing options
            tablesSelect.innerHTML = '';
            
            // Add tables to dropdown
            data.tables.forEach(table => {
                const option = document.createElement('option');
                option.value = table;
                option.textContent = table;
                tablesSelect.appendChild(option);
            });
            
            // Also add tables to search form
            const searchTablesContainer = document.getElementById('search-tables');
            if (searchTablesContainer) {
                data.tables.forEach(table => {
                    const div = document.createElement('div');
                    div.className = 'form-check';
                    
                    const input = document.createElement('input');
                    input.type = 'checkbox';
                    input.className = 'form-check-input';
                    input.id = `table-${table}`;
                    input.value = table;
                    input.checked = table === 'emails'; // Check emails by default
                    
                    const label = document.createElement('label');
                    label.className = 'form-check-label';
                    label.htmlFor = `table-${table}`;
                    label.textContent = table;
                    
                    div.appendChild(input);
                    div.appendChild(label);
                    searchTablesContainer.appendChild(div);
                });
            }
        })
        .catch(error => {
            console.error('Error loading tables:', error);
            showError('Failed to load database tables');
        });
}

function runQuery() {
    const queryInput = document.getElementById('sql-query');
    const resultsContainer = document.getElementById('query-results');
    
    if (!queryInput || !resultsContainer) return;
    
    const query = queryInput.value.trim();
    if (!query) {
        showError('Please enter a SQL query');
        return;
    }
    
    if (!query.toLowerCase().startsWith('select')) {
        showError('Only SELECT queries are allowed for security reasons');
        return;
    }
    
    // Show loading indicator
    resultsContainer.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    
    fetch('/api/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<div class="alert alert-info">Query returned no results</div>';
            return;
        }
        
        // Create table from results
        const table = document.createElement('table');
        table.className = 'table table-striped table-hover';
        
        // Create header row
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        Object.keys(data[0]).forEach(key => {
            const th = document.createElement('th');
            th.textContent = key;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create body rows
        const tbody = document.createElement('tbody');
        data.forEach(row => {
            const tr = document.createElement('tr');
            Object.values(row).forEach(value => {
                const td = document.createElement('td');
                td.textContent = value;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        
        // Display the table
        resultsContainer.innerHTML = '';
        resultsContainer.appendChild(table);
        
        // Add download options
        const downloadDiv = document.createElement('div');
        downloadDiv.className = 'mt-3';
        downloadDiv.innerHTML = `<button class="btn btn-sm btn-outline-secondary" onclick="downloadResults('csv')">Download CSV</button>
                                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="downloadResults('xlsx')">Download Excel</button>
                                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="downloadResults('json')">Download JSON</button>`;
        resultsContainer.appendChild(downloadDiv);
        
        // Store results in a global variable for download
        window.queryResults = data;
    })
    .catch(error => {
        console.error('Error running query:', error);
        resultsContainer.innerHTML = '<div class="alert alert-danger">Failed to run query. Check console for details.</div>';
    });
}

function searchDatabase() {
    const searchTerm = document.getElementById('search-term').value.trim();
    const resultsContainer = document.getElementById('search-results');
    
    if (!searchTerm || !resultsContainer) return;
    
    // Get selected tables
    const selectedTables = [];
    document.querySelectorAll('#search-tables input:checked').forEach(checkbox => {
        selectedTables.push(checkbox.value);
    });
    
    if (selectedTables.length === 0) {
        showError('Please select at least one table to search');
        return;
    }
    
    // Show loading indicator
    resultsContainer.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    
    fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            term: searchTerm,
            tables: selectedTables 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        // Clear results
        resultsContainer.innerHTML = '';
        
        // Display results for each table
        for (const table in data) {
            const results = data[table];
            
            const tableDiv = document.createElement('div');
            tableDiv.className = 'mb-4';
            
            const tableHeading = document.createElement('h5');
            tableHeading.textContent = table + ' (' + results.length + ' results)';
            tableDiv.appendChild(tableHeading);
            
            if (results.error) {
                tableDiv.innerHTML += '<div class="alert alert-danger">' + results.error + '</div>';
                resultsContainer.appendChild(tableDiv);
                continue;
            }
            
            if (results.length === 0) {
                tableDiv.innerHTML += '<div class="alert alert-info">No matches found</div>';
                resultsContainer.appendChild(tableDiv);
                continue;
            }
            
            // Create table
            const table = document.createElement('table');
            table.className = 'table table-sm table-striped table-hover';
            
            // Create header row
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            Object.keys(results[0]).forEach(key => {
                const th = document.createElement('th');
                th.textContent = key;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body rows (limit to first 100 for performance)
            const tbody = document.createElement('tbody');
            results.slice(0, 100).forEach(row => {
                const tr = document.createElement('tr');
                Object.values(row).forEach(value => {
                    const td = document.createElement('td');
                    td.textContent = value;
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            
            tableDiv.appendChild(table);
            resultsContainer.appendChild(tableDiv);
        }
    })
    .catch(error => {
        console.error('Error searching database:', error);
        resultsContainer.innerHTML = '<div class="alert alert-danger">Failed to search database. Check console for details.</div>';
    });
}

function setupReportButtons() {
    const reportsContainer = document.getElementById('reports-container');
    if (!reportsContainer) return;
    
    reportsContainer.innerHTML = '<div class="report-wrapper">' +
        '<div class="list-group mb-3">' +
            '<a href="/api/report?type=full&format=csv" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">' +
                'Full Database Report (CSV)' +
                '<i class="fas fa-download"></i>' +
            '</a>' +
            '<a href="/api/report?type=full&format=xlsx" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">' +
                'Full Database Report (Excel)' +
                '<i class="fas fa-download"></i>' +
            '</a>' +
            '<a href="/api/report?type=emails&format=csv" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">' +
                'Emails Report (CSV)' +
                '<i class="fas fa-download"></i>' +
            '</a>' +
            '<a href="/api/report?type=images&format=csv" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">' +
                'Images Report (CSV)' +
                '<i class="fas fa-download"></i>' +
            '</a>' +
            '<a href="/api/report?type=documents&format=csv" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">' +
                'Documents Report (CSV)' +
                '<i class="fas fa-download"></i>' +
            '</a>' +
        '</div>' +
    '</div>';
}

function downloadResults(format) {
    if (!window.queryResults) return;
    
    try {
        let content, filename, type;
        
        if (format === 'json') {
            content = JSON.stringify(window.queryResults);
            filename = 'query_results.json';
            type = 'application/json';
        } 
        else if (format === 'csv') {
            // Convert to CSV
            if (!window.queryResults.length) return;
            
            const headers = Object.keys(window.queryResults[0]).join(',');
            const rows = window.queryResults.map(row => {
                return Object.values(row).map(value => {
                    return '"' + String(value).replace(/"/g, '""') + '"';
                }).join(',');
            }).join('\n');
            
            content = headers + '\n' + rows;
            filename = 'query_results.csv';
            type = 'text/csv';
        }
        else {
            alert('Download format not supported in the browser. Use the server-side report feature instead.');
            return;
        }
        
        // Create download link
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
    catch (error) {
        console.error('Error downloading results:', error);
        alert('Failed to download results');
    }
}

function showError(message) {
    alert(message);
}
