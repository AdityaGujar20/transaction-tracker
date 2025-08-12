// DOM Elements
const uploadForm = document.getElementById("uploadForm");
const pdfFile = document.getElementById("pdfFile");
const uploadArea = document.getElementById("uploadArea");
const uploadTitle = document.getElementById("uploadTitle");
const uploadSubtext = document.getElementById("uploadSubtext");
const submitBtn = document.getElementById("submitBtn");
const statusMessage = document.getElementById("statusMessage");
const analysisSection = document.getElementById("analysisSection");
const refreshBtn = document.getElementById("refreshBtn");
const resultsPanel = document.getElementById("resultsPanel");
const resultsContent = document.getElementById("resultsContent");

// Global variable to track if upload is in progress
let isUploading = false;

// File upload handling - Fixed for first-time upload issue
pdfFile.addEventListener("change", function(e) {
    const file = e.target.files[0];
    if (file) {
        if (file.type === 'application/pdf') {
            updateUploadUI(file);
            enableSubmitButton();
            hideStatusMessage(); // Clear any previous error messages
        } else {
            showStatusMessage("Please select a valid PDF file", "error");
            resetUploadUI();
            disableSubmitButton();
        }
    } else {
        resetUploadUI();
        disableSubmitButton();
    }
});

// Drag and drop functionality - Enhanced
uploadArea.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', function(e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove('dragover');
});

uploadArea.addEventListener('drop', function(e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
            // Manually set the file to the input
            const dt = new DataTransfer();
            dt.items.add(file);
            pdfFile.files = dt.files;
            
            updateUploadUI(file);
            enableSubmitButton();
            hideStatusMessage();
        } else {
            showStatusMessage("Please select a valid PDF file", "error");
        }
    }
});

// Click to upload
uploadArea.addEventListener('click', function(e) {
    if (!isUploading) {
        pdfFile.click();
    }
});

// Form submission - Enhanced with better error handling
uploadForm.addEventListener("submit", async function(e) {
    e.preventDefault();

    if (isUploading) {
        return; // Prevent multiple submissions
    }

    const file = pdfFile.files[0];
    if (!file) {
        showStatusMessage("Please select a PDF file", "error");
        return;
    }

    if (file.type !== 'application/pdf') {
        showStatusMessage("Please select a valid PDF file", "error");
        return;
    }

    // Set uploading state
    isUploading = true;
    setLoadingState(true);
    hideStatusMessage();

    const formData = new FormData();
    formData.append("pdf", file);

    try {
        const res = await fetch("/pipeline/run-pipeline", { 
            method: "POST", 
            body: formData 
        });
        
        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`HTTP error! status: ${res.status}. ${errorText}`);
        }
        
        const data = await res.json();
        
        if (data.message && data.message.includes("completed")) {
            showStatusMessage("✅ Analysis completed successfully!", "success");
            showAnalysisSection();
        } else if (data.message) {
            showStatusMessage(data.message, "success");
            showAnalysisSection();
        } else {
            showStatusMessage("✅ File processed successfully!", "success");
            showAnalysisSection();
        }
    } catch (err) {
        console.error("Upload error:", err);
        showStatusMessage(`❌ Error: ${err.message}`, "error");
    } finally {
        isUploading = false;
        setLoadingState(false);
    }
});

// Analysis card click handlers - Fixed for better visibility
document.addEventListener('DOMContentLoaded', function() {
    const analysisCards = document.querySelectorAll('.analysis-card[data-endpoint]');
    
    analysisCards.forEach(card => {
        // Create card flip structure
        createFlippableCard(card);
        
        card.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const endpoint = this.getAttribute('data-endpoint');
            if (endpoint && !this.classList.contains('flipped')) {
                flipCard(this, endpoint);
            }
        });
    });
});

// Create flippable card structure - Enhanced
function createFlippableCard(card) {
    const originalContent = card.innerHTML;
    
    card.innerHTML = `
        <div class="card-inner">
            <div class="card-front">
                ${originalContent}
            </div>
            <div class="card-back">
                <div class="card-back-content">
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        <p>Loading data...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Function to flip card and fetch data - Enhanced with better error handling
async function flipCard(card, endpoint) {
    try {
        // Flip the card first
        card.classList.add('flipped');
        
        // Get the back content area
        const backContent = card.querySelector('.card-back-content');
        
        // Show loading state
        backContent.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <p>Fetching data...</p>
            </div>
        `;
        
        const res = await fetch(endpoint);
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        
        // Format and display the data on the back of the card
        let formattedData;
        if (typeof data === 'object') {
            formattedData = JSON.stringify(data, null, 2);
        } else {
            formattedData = String(data);
        }
        
        backContent.innerHTML = `
            <div class="json-content">${formattedData}</div>
            <button class="flip-back-btn" onclick="flipCardBack(this)">
                <svg viewBox="0 0 24 24" width="16" height="16">
                    <path d="M19 12H5M12 19l-7-7 7-7"/>
                </svg>
                Back to Front
            </button>
        `;
        
    } catch (err) {
        console.error("Fetch error:", err);
        const backContent = card.querySelector('.card-back-content');
        backContent.innerHTML = `
            <div class="error-content">
                <p>❌ Error fetching data</p>
                <p style="font-size: 0.75rem; margin-top: 0.5rem;">${err.message}</p>
                <button class="flip-back-btn" onclick="flipCardBack(this)">
                    <svg viewBox="0 0 24 24" width="16" height="16">
                        <path d="M19 12H5M12 19l-7-7 7-7"/>
                    </svg>
                    Back to Front
                </button>
            </div>
        `;
    }
}

// Global function to flip card back
function flipCardBack(button) {
    const card = button.closest('.analysis-card');
    if (card) {
        card.classList.remove('flipped');
    }
}

// Refresh data functionality - Enhanced
refreshBtn.addEventListener("click", async function() {
    const confirmRefresh = confirm(
        "⚠️ Are you sure you want to refresh and delete all processed data?\n\nThis action cannot be undone."
    );
    
    if (!confirmRefresh) return;

    try {
        // Show loading state
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = `
            <div class="loading-spinner"></div>
            Refreshing...
        `;

        const response = await fetch("/refresh-data", { 
            method: "DELETE" 
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}. ${errorText}`);
        }
        
        const data = await response.json();
        
        // Reset UI
        showStatusMessage("✅ " + (data.message || "Data refreshed successfully"), "success");
        hideAnalysisSection();
        hideResultsPanel();
        resetFileUpload();
        
        // Reset all flipped cards
        document.querySelectorAll('.analysis-card.flipped').forEach(card => {
            card.classList.remove('flipped');
        });
        
    } catch (err) {
        console.error("Refresh error:", err);
        showStatusMessage(`❌ Error refreshing data: ${err.message}`, "error");
    } finally {
        // Reset button
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = `
            <svg class="refresh-icon" viewBox="0 0 24 24">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh Data
        `;
    }
});

// Helper Functions - Enhanced
function updateUploadUI(file) {
    uploadTitle.textContent = "✅ File Selected";
    uploadSubtext.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    uploadArea.classList.add('file-selected');
}

function resetUploadUI() {
    uploadTitle.textContent = "Upload PDF Statement";
    uploadSubtext.textContent = "Drag and drop your file here or click to browse";
    uploadArea.classList.remove('file-selected');
}

function enableSubmitButton() {
    submitBtn.disabled = false;
}

function disableSubmitButton() {
    submitBtn.disabled = true;
}

function showStatusMessage(message, type = "") {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.add('show');
    
    // Auto-hide success messages after 5 seconds
    if (type === "success") {
        setTimeout(() => {
            if (statusMessage.classList.contains('show') && statusMessage.classList.contains('success')) {
                statusMessage.classList.remove('show');
            }
        }, 5000);
    }
}

function hideStatusMessage() {
    statusMessage.classList.remove('show');
}

function setLoadingState(loading) {
    if (loading) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <div class="loading-spinner"></div>
            <span>Processing...</span>
        `;
        uploadArea.style.pointerEvents = 'none';
    } else {
        submitBtn.disabled = pdfFile.files.length === 0;
        submitBtn.innerHTML = `
            <span>Analyze Now</span>
            <svg class="btn-arrow" viewBox="0 0 24 24">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12,5 19,12 12,19"/>
            </svg>
        `;
        uploadArea.style.pointerEvents = 'auto';
    }
}

function showAnalysisSection() {
    analysisSection.classList.add('show');
}

function hideAnalysisSection() {
    analysisSection.classList.remove('show');
}

function showResultsPanel() {
    resultsPanel.classList.add('show');
}

function hideResultsPanel() {
    resultsPanel.classList.remove('show');
}

function closeResults() {
    hideResultsPanel();
}

function resetFileUpload() {
    pdfFile.value = "";
    resetUploadUI();
    disableSubmitButton();
    isUploading = false;
}

// Global functions for HTML references
window.closeResults = closeResults;
window.flipCardBack = flipCardBack;

// Initialize app - Enhanced
document.addEventListener("DOMContentLoaded", function() {
    // Initial state
    hideStatusMessage();
    disableSubmitButton();
    
    // Add smooth scrolling for better UX
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Check if there are existing files on page load
    if (pdfFile.files.length > 0) {
        updateUploadUI(pdfFile.files[0]);
        enableSubmitButton();
    }
    
    console.log("Transaction Tracker App initialized successfully!");
});