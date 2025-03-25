// Email search functionality
function searchEmails() {
  const keyword = document.getElementById('search-keyword').value;
  const field = document.getElementById('search-field').value;
  const resultsContainer = document.getElementById('search-results');
  
  // Show loading indicator
  resultsContainer.innerHTML = '<p>Searching...</p>';
  
  // Call the API
  fetch(`/api/search?keyword=${encodeURIComponent(keyword)}&field=${field}&limit=100`)
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        if (data.count === 0) {
          resultsContainer.innerHTML = '<p>No results found.</p>';
        } else {
          // Display results
          let html = `<h4>Found ${data.count} results:</h4><div class="results-list">`;
          
          data.results.forEach(email => {
            html += `
              <div class="email-result">
                <h5>${email.subject || '(No subject)'}</h5>
                <p><strong>From:</strong> ${email.sender || 'Unknown'}</p>
                <p><strong>Date:</strong> ${email.date || 'Unknown'}</p>
                <p class="email-preview">${email.content?.substring(0, 150) || '(No content)'}...</p>
                <button onclick="viewFullEmail(${email.id})">View Full Email</button>
              </div>
            `;
          });
          
          html += '</div>';
          resultsContainer.innerHTML = html;
        }
      } else {
        resultsContainer.innerHTML = `<p>Error: ${data.error}</p>`;
      }
    })
    .catch(error => {
      resultsContainer.innerHTML = `<p>Error: ${error}</p>`;
    });
}

// Function to view full email content (add to existing JS file)
function viewFullEmail(emailId) {
  // You may already have this function, adjust as needed
  window.location.href = `/email/${emailId}`;
  // Or open a modal with the full content
}