// Main application JavaScript

// Create a global namespace for our app functions
window.OllamaRecruitPro = window.OllamaRecruitPro || {};

// Global variables to store state
let jdId = null;
let cvIds = [];
let totalFiles = 0;
let processedFiles = 0;

// Function to initialize the page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Application initialized');
    console.log('displayMatchResults function available:', typeof window.displayMatchResults === 'function');
    console.log('OllamaRecruitPro.displayMatchResults available:', typeof window.OllamaRecruitPro.displayMatchResults === 'function');
    console.log('handleJDUploadResponse function available:', typeof window.handleJDUploadResponse === 'function');
    console.log('displayJobDescription function available:', typeof window.displayJobDescription === 'function');
    
    // Initialize the matches container if it doesn't exist
    ensureMatchesContainer();
    
    // Check for current status
    checkStatus();
    
    // Attach event listeners to uploadJDBtn if using click instead of form submit
    if (document.getElementById('uploadJDBtn')) {
        document.getElementById('uploadJDBtn').addEventListener('click', function() {
            const form = document.getElementById('uploadJDForm');
            if (form) {
                // Trigger the form submit event
                const submitEvent = new Event('submit', { cancelable: true });
                form.dispatchEvent(submitEvent);
            } else {
                console.error('Upload JD form not found');
            }
        });
    }

    // Clear any error messages
    clearErrors();
});

// Ensure the matches container exists
function ensureMatchesContainer() {
    let container = document.getElementById('matches-container');
    if (!container) {
        console.log('Creating matches container');
        container = document.createElement('div');
        container.id = 'matches-container';
        container.className = 'mb-5';
        
        // Find a suitable parent to append to
        const contentSection = document.querySelector('.content-section') || 
                              document.querySelector('.container') || 
                              document.body;
        if (contentSection) {
            contentSection.appendChild(container);
        } else {
            document.body.appendChild(container);
        }
    }
    
    container.style.display = 'block';
    return container;
}

// Check the current application status
async function checkStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        
        // Update UI based on status
        if (data.session_info && data.session_info.has_jd) {
            // Get the current JD ID
            const jdResponse = await fetch('/current_jd');
            const jdData = await jdResponse.json();
            
            if (jdData.success) {
                jdId = jdData.job_description.id || 1; // Use 1 as fallback
                console.log('Current JD ID:', jdId);
                
                // Update UI to show JD is loaded
                const jdStatusElement = document.getElementById('jd-status-text');
                if (jdStatusElement) {
                    jdStatusElement.innerHTML = '<i class="fas fa-check-circle text-success"></i> Job Description uploaded';
                }
                
                const jdSection = document.getElementById('jd-upload-section');
                if (jdSection) {
                    jdSection.classList.add('uploaded');
                }
            }
        }
        
        if (data.session_info && data.session_info.uploaded_candidates_count > 0) {
            // Set cvIds - we'll need to get the actual IDs from somewhere
            cvIds = data.session_info.uploaded_candidate_ids || [];
            console.log('Found candidates:', cvIds.length);
        }
        
        // Update match button state
        updateMatchButton();
        
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Helper function to show status messages
function showStatus(elementId, message, type) {
    const statusElement = document.getElementById(elementId);
    if (!statusElement) {
        console.error(`Status element ${elementId} not found`);
        return;
    }
    
    statusElement.className = `alert alert-${type}`;
    statusElement.textContent = message;
    statusElement.style.display = 'block';
    
    // Optionally hide after a delay
    setTimeout(() => statusElement.style.display = 'none', 5000);
}

// Update the match button state based on current data
function updateMatchButton() {
    const matchButton = document.getElementById('matchButton');
    if (!matchButton) {
        console.error('Match button not found');
        return;
    }
    
    matchButton.disabled = !jdId || cvIds.length === 0;
}

// Function to clear error messages
function clearErrors() {
    const errorElements = document.querySelectorAll('.alert-danger');
    errorElements.forEach(element => {
        element.style.display = 'none';
    });
    
    // Also clear specific error elements
    const jdProcessingError = document.getElementById('jdProcessingError');
    if (jdProcessingError) {
        jdProcessingError.style.display = 'none';
    }
}

// Function to display match results
function displayMatchResults(results) {
    console.log("Displaying match results:", results);
    
    // Ensure matches container exists
    const container = ensureMatchesContainer();
    
    // Clear any previous content
    container.innerHTML = '';
    
    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <div class="alert alert-warning mt-3">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        No matches found for this job description and set of candidates.
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    // Create a header for the results
    const headerHtml = `
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-users me-2"></i>Match Results</h5>
            </div>
            <div class="card-body">
                <h5 class="mb-4">Found ${results.length} matching candidate(s)</h5>
                <div class="results-container"></div>
            </div>
        </div>
    `;
    container.innerHTML = headerHtml;
    
    const resultsBody = container.querySelector('.results-container');
    if (!resultsBody) {
        console.error("Could not find results container");
        return;
    }
    
    // Display each match
    results.forEach(match => {
        const candidateInfo = match.candidate_info || {};
        const matchElement = document.createElement('div');
        matchElement.className = 'match-card mb-3';
        
        // Calculate score percentage if not provided
        const scorePercent = match.score_percent || Math.round(match.score * 100);
        
        // Function to get color based on score
        const getScoreColor = (score) => {
            const scoreNum = parseFloat(score);
            if (scoreNum >= 85) return 'success';
            if (scoreNum >= 70) return 'primary';
            if (scoreNum >= 50) return 'warning';
            return 'danger';
        };
        
        // Create skills match HTML
        let skillsMatchHtml = '';
        if (match.skills_match && match.skills_match.length > 0) {
            skillsMatchHtml = '<div class="skills-match mb-2">';
            match.skills_match.slice(0, 5).forEach(skill => {
                skillsMatchHtml += `<span class="skill-match">${skill}</span> `;
            });
            skillsMatchHtml += '</div>';
        }
        
        // Create skills gap HTML
        let skillsGapHtml = '';
        if (match.skills_gap && match.skills_gap.length > 0) {
            skillsGapHtml = '<div class="skills-gap mb-2">';
            match.skills_gap.slice(0, 3).forEach(skill => {
                skillsGapHtml += `<span class="skill-gap">${skill}</span> `;
            });
            skillsGapHtml += '</div>';
        }
        
        // Create the match card HTML
        matchElement.innerHTML = `
            <div class="row align-items-center">
                <div class="col-md-2 text-center">
                    <div class="match-score">
                        <div class="progress" style="height: 6px; margin-bottom: 8px;">
                            <div class="progress-bar bg-${getScoreColor(scorePercent)}" role="progressbar" 
                                style="width: ${scorePercent}%" aria-valuenow="${scorePercent}" 
                                aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <span style="color: var(--${getScoreColor(scorePercent)}-color);">${scorePercent}%</span>
                    </div>
                </div>
                <div class="col-md-8">
                    <h5 class="mb-1">${candidateInfo.name || 'Candidate'}</h5>
                    <p class="text-muted mb-2">${candidateInfo.email || ''} ${candidateInfo.phone ? ' | ' + candidateInfo.phone : ''}</p>
                    
                    ${skillsMatchHtml}
                    ${skillsGapHtml}
                    
                    <div class="candidate-summary mt-2">
                        <p class="mb-0">${match.summary || 'No summary available.'}</p>
                    </div>
                </div>
                <div class="col-md-2 text-center">
                    <button class="btn btn-sm btn-outline-primary view-details-btn" 
                        data-candidate-id="${match.candidate_id}" 
                        onclick="showCandidateDetails(${match.candidate_id})">
                        <i class="fas fa-user me-1"></i> Details
                    </button>
                </div>
            </div>
        `;
        
        resultsBody.appendChild(matchElement);
    });
    
    // Add the view details event listeners
    addViewDetailsListeners();
}

// Function to show candidate details in a modal
function showCandidateDetails(candidateId) {
    console.log("Showing candidate details for ID:", candidateId);
    
    // Check if modal already exists
    let modalElement = document.getElementById('candidateDetailModal');
    
    // If no modal exists, use the function to ensure it exists
    if (!modalElement) {
        modalElement = ensureCandidateModal();
    }
    
    // Show loading indicator in modal body
    const modalBody = document.getElementById('candidateDetailModalBody');
    if (modalBody) {
        modalBody.innerHTML = `
            <div class="text-center p-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Loading candidate details...</p>
            </div>
        `;
    }
    
    // Show the modal
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Fetch candidate details
    fetch(`/get_candidate/${candidateId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update modal with candidate details
                const candidate = data.candidate;
                
                if (modalBody) {
                    modalBody.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Contact Information</h6>
                                <p><strong>Name:</strong> ${candidate.name || 'Not specified'}</p>
                                <p><strong>Email:</strong> ${candidate.email || 'Not specified'}</p>
                                <p><strong>Phone:</strong> ${candidate.phone || 'Not specified'}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Skills</h6>
                                <div class="skill-tags">
                                    ${candidate.skills && candidate.skills.length > 0 
                                        ? candidate.skills.map(skill => `<span class="badge bg-primary me-1 mb-1">${skill}</span>`).join('') 
                                        : 'No skills specified'}
                                </div>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Experience</h6>
                                ${candidate.experience && candidate.experience.length > 0 
                                    ? `<ul class="list-group">${candidate.experience.map(exp => `<li class="list-group-item">${exp}</li>`).join('')}</ul>` 
                                    : '<p>No experience details provided</p>'}
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Education</h6>
                                ${candidate.education && candidate.education.length > 0 
                                    ? `<ul class="list-group">${candidate.education.map(edu => `<li class="list-group-item">${edu}</li>`).join('')}</ul>` 
                                    : '<p>No education details provided</p>'}
                            </div>
                        </div>
                        
                        ${candidate.summary ? `
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Summary</h6>
                                <p>${candidate.summary}</p>
                            </div>
                        </div>
                        ` : ''}
                    `;
                }
            } else {
                throw new Error(data.error || 'Failed to load candidate details');
            }
        })
        .catch(error => {
            console.error('Error fetching candidate details:', error);
            if (modalBody) {
                modalBody.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error loading candidate details: ${error.message}
                    </div>
                `;
            }
        });
}

// Ensure candidate modal exists
function ensureCandidateModal() {
    let modalElement = document.getElementById('candidateDetailModal');
    
    if (!modalElement) {
        modalElement = document.createElement('div');
        modalElement.className = 'modal fade';
        modalElement.id = 'candidateDetailModal';
        modalElement.tabIndex = '-1';
        modalElement.setAttribute('aria-labelledby', 'candidateDetailModalLabel');
        modalElement.setAttribute('aria-hidden', 'true');
        
        modalElement.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="candidateDetailModalLabel">Candidate Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="candidateDetailModalBody">
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalElement);
    }
    
    return modalElement;
}

// Add event listeners for view details buttons
function addViewDetailsListeners() {
    const viewDetailsButtons = document.querySelectorAll('.view-details-btn');
    
    viewDetailsButtons.forEach(button => {
        button.addEventListener('click', () => {
            const candidateId = button.getAttribute('data-candidate-id');
            showCandidateDetails(candidateId);
        });
    });
}

// Make functions available globally
window.displayMatchResults = displayMatchResults;
window.showCandidateDetails = showCandidateDetails;
window.addViewDetailsListeners = addViewDetailsListeners;

// Create a global namespace for the app
window.OllamaRecruitPro = {
    displayMatchResults: displayMatchResults,
    showCandidateDetails: showCandidateDetails,
    addViewDetailsListeners: addViewDetailsListeners
};