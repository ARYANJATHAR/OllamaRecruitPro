// Job Description Display Functionality

// Function to display job description data in the UI
function displayJobDescription(jdData) {
    console.log('Displaying JD data:', jdData);
    
    if (!jdData) {
        console.error('No job description data to display');
        return;
    }
    
    // Find or create the job description display container
    let jdDisplayContainer = document.querySelector('.job-description-display');
    if (!jdDisplayContainer) {
        console.log('Creating JD display container');
        jdDisplayContainer = document.createElement('div');
        jdDisplayContainer.className = 'job-description-display card mb-4';
        
        // Find a suitable location to insert it
        const jdCard = document.querySelector('.card:nth-child(1)');
        if (jdCard && jdCard.parentNode) {
            jdCard.parentNode.insertBefore(jdDisplayContainer, jdCard.nextSibling);
        } else {
            const jdSection = document.querySelector('.col-md-6:first-child');
            if (jdSection) {
                jdSection.appendChild(jdDisplayContainer);
            } else {
                document.body.appendChild(jdDisplayContainer);
            }
        }
    }
    
    // Extract data from job description
    const title = jdData.title || 'Job Position';
    const company = jdData.company || 'Company';
    const fullDescription = jdData.description || '';
    
    // Try to extract sections from full description
    let responsibilities = [];
    let qualifications = [];
    
    // Extract responsibilities and qualifications from description text
    if (fullDescription) {
        // Look for Responsibilities section
        if (fullDescription.includes('Responsibilities:')) {
            const respSection = fullDescription.split('Responsibilities:')[1].split(/Qualifications:|Requirements:/)[0];
            responsibilities = respSection.split(/\n\s*\n/)[0]  // Get first paragraph
                .split(/\n-|\n•|\n\d+\./)  // Split by bullet points or numbered lists
                .filter(item => item.trim().length > 0)
                .map(item => item.trim());
        }
        
        // Look for Qualifications section
        if (fullDescription.includes('Qualifications:')) {
            const qualSection = fullDescription.split('Qualifications:')[1].split(/\n\s*\n/)[0];
            qualifications = qualSection
                .split(/\n-|\n•|\n\d+\./)  // Split by bullet points or numbered lists
                .filter(item => item.trim().length > 0)
                .map(item => item.trim());
        } else if (fullDescription.includes('Requirements:')) {
            // Alternative section name
            const qualSection = fullDescription.split('Requirements:')[1].split(/\n\s*\n/)[0];
            qualifications = qualSection
                .split(/\n-|\n•|\n\d+\./)  // Split by bullet points or numbered lists
                .filter(item => item.trim().length > 0)
                .map(item => item.trim());
        }
    }
    
    // Use original required skills as fallback for responsibilities
    if (responsibilities.length === 0 && Array.isArray(jdData.required_skills)) {
        responsibilities = jdData.required_skills;
    }
    
    // Use original preferred skills as fallback for qualifications
    if (qualifications.length === 0 && Array.isArray(jdData.preferred_skills)) {
        qualifications = jdData.preferred_skills;
    }
    
    const experience = jdData.required_experience || 'Not specified';
    const education = jdData.required_education || 'Not specified';
    
    // Create responsibilities HTML
    let responsibilitiesHtml = '<p class="text-muted">None specified</p>';
    if (responsibilities.length > 0) {
        responsibilitiesHtml = '<ul class="list-unstyled">';
        responsibilities.forEach(item => {
            responsibilitiesHtml += `<li><i class="fas fa-check-circle text-success me-2"></i>${item}</li>`;
        });
        responsibilitiesHtml += '</ul>';
    }
    
    // Create qualifications HTML
    let qualificationsHtml = '<p class="text-muted">None specified</p>';
    if (qualifications.length > 0) {
        qualificationsHtml = '<ul class="list-unstyled">';
        qualifications.forEach(item => {
            qualificationsHtml += `<li><i class="fas fa-check-circle text-primary me-2"></i>${item}</li>`;
        });
        qualificationsHtml += '</ul>';
    }
    
    // Build the HTML for the job description display
    jdDisplayContainer.innerHTML = `
        <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-briefcase me-2"></i>Current Job Description</h5>
        </div>
        <div class="card-body">
            <h4 class="card-title">${title}</h4>
            <h6 class="card-subtitle mb-3 text-muted">${company}</h6>
            
            <div class="job-description-text mb-4">
                ${fullDescription ? fullDescription.split('Responsibilities:')[0].trim() : 'No description provided'}
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6><i class="fas fa-tasks me-2"></i>Responsibilities</h6>
                    ${responsibilitiesHtml}
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-graduation-cap me-2"></i>Qualifications</h6>
                    ${qualificationsHtml}
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-briefcase me-2"></i>Required Experience</h6>
                    <p class="mb-0">${experience}</p>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-user-graduate me-2"></i>Required Education</h6>
                    <p class="mb-0">${education}</p>
                </div>
            </div>
        </div>
    `;
    
    // Also display in modal if it exists
    const modalBody = document.getElementById('jobDescriptionModalBody');
    if (modalBody) {
        modalBody.innerHTML = jdDisplayContainer.innerHTML;
    }
    
    // Make the view button visible if it exists
    const viewJobDescriptionBtn = document.getElementById('viewJobDescriptionBtn');
    if (viewJobDescriptionBtn) {
        viewJobDescriptionBtn.style.display = 'inline-block';
    }
}

// Function to handle job description upload response
function handleJDUploadResponse(response) {
    console.log('JD upload response received:', response);
    
    if (response.success) {
        // Set the global job ID
        if (window.jdId !== undefined) {
            window.jdId = response.jd_id;
        } else if (typeof jdId !== 'undefined') {
            jdId = response.jd_id;
        }
        
        // Display success message
        const statusElem = document.getElementById('jdStatus');
        if (statusElem) {
            statusElem.innerHTML = `<i class="fas fa-check-circle me-2"></i>${response.message || 'Job description uploaded successfully'}`;
            statusElem.className = 'alert alert-success';
            statusElem.style.display = 'block';
        }
        
        // Update the job description display
        displayJobDescription(response.jd_data);
        
        // Update the UI to show the JD is ready
        const jdStatusText = document.getElementById('jd-status-text');
        if (jdStatusText) {
            jdStatusText.innerHTML = '<i class="fas fa-check-circle text-success"></i> Job Description uploaded';
        }
        
        // Hide loader if it exists
        const loader = document.getElementById('jdLoader');
        if (loader) {
            loader.style.display = 'none';
        }
        
        // Show matching controls
        const noJdMessage = document.getElementById('no-jd-message');
        if (noJdMessage) {
            noJdMessage.style.display = 'none';
        }
        
        const matchingControls = document.getElementById('matching-controls');
        if (matchingControls) {
            matchingControls.style.display = 'block';
        }
        
        // Update match button state
        if (typeof updateMatchButton === 'function') {
            updateMatchButton();
        }
        
    } else {
        console.error('Error processing job description:', response.error);
        
        // Show error message
        const errorElem = document.getElementById('jdProcessingError');
        if (errorElem) {
            errorElem.style.display = 'block';
        }
        
        const errorMsgElem = document.getElementById('jdErrorMessage');
        if (errorMsgElem) {
            errorMsgElem.textContent = response.error || 'Error processing job description';
        }
        
        // Hide the loading indicator
        const statusElem = document.getElementById('jdStatus');
        if (statusElem) {
            statusElem.style.display = 'none';
        }
    }
}

// Make functions available globally
window.displayJobDescription = displayJobDescription;
window.handleJDUploadResponse = handleJDUploadResponse;

// Attach event listener for job description form submission
document.addEventListener('DOMContentLoaded', function() {
    console.log('JD-display.js: Setting up form submission handler');
    const jdForm = document.getElementById('jdForm');
    
    if (jdForm) {
        jdForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('JD form submission detected');
            
            const fileInput = document.getElementById('jdFile');
            if (!fileInput || !fileInput.files[0]) {
                alert('Please select a job description file to upload.');
                return;
            }
            
            const formData = new FormData();
            formData.append('jd_file', fileInput.files[0]);
            
            // Show loading indicator
            const statusElem = document.getElementById('jdStatus');
            if (statusElem) {
                statusElem.className = 'alert alert-info';
                statusElem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span>Uploading and processing job description...</span>
                    </div>
                `;
                statusElem.style.display = 'block';
            }
            
            // Hide any previous error
            const errorElem = document.getElementById('jdProcessingError');
            if (errorElem) {
                errorElem.style.display = 'none';
            }
            
            // Show loader if exists
            const loader = document.getElementById('jdLoader');
            if (loader) {
                loader.style.display = 'block';
            }
            
            console.log('Sending JD upload request to server');
            fetch('/upload_jd', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('JD upload response received with status:', response.status);
                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('JD upload response parsed:', data);
                handleJDUploadResponse(data);
            })
            .catch(error => {
                console.error('Error uploading job description:', error);
                
                // Show error message
                if (errorElem) {
                    errorElem.style.display = 'block';
                    
                    const errorMsgElem = document.getElementById('jdErrorMessage');
                    if (errorMsgElem) {
                        errorMsgElem.textContent = 'Error uploading job description: ' + error.message;
                    }
                }
                
                // Hide the loading indicator
                if (statusElem) {
                    statusElem.style.display = 'none';
                }
                
                // Hide loader
                if (loader) {
                    loader.style.display = 'none';
                }
            });
        });
        console.log('JD form submission handler attached');
    } else {
        console.error('JD form not found!');
    }
});
