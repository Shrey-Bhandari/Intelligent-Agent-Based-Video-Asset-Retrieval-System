/* ========================================
   STATE MANAGEMENT
   ======================================== */

const API_BASE = 'http://localhost:8000';

const STATE = {
    file: null,
    processing: false,
    results: null,
    summary: null,
    sessionId: null,
    progressInterval: null,
};

/* ========================================
   DOM ELEMENTS
   ======================================== */

const DOM = {
    uploadBox: document.getElementById('uploadBox'),
    fileInput: document.getElementById('fileInput'),
    processBtn: document.getElementById('processBtn'),
    loadingContainer: document.getElementById('loadingContainer'),
    resultsSection: document.getElementById('resultsSection'),
    errorContainer: document.getElementById('errorContainer'),
    resultsContainer: document.getElementById('resultsContainer'),
    summaryTotal: document.getElementById('summaryTotal'),
    summarySuccess: document.getElementById('summarySuccess'),
    summaryFailure: document.getElementById('summaryFailure'),
    errorMessage: document.getElementById('errorMessage'),
    resetBtn: document.getElementById('resetBtn'),
    errorResetBtn: document.getElementById('errorResetBtn'),
    downloadReportBtn: document.getElementById('downloadReportBtn'),
};

/* ========================================
   FILE UPLOAD HANDLING
   ======================================== */

function initializeUpload() {
    // Click to upload - both on box and link
    const uploadLink = DOM.uploadBox.querySelector('.upload-link');
    
    DOM.uploadBox.addEventListener('click', (e) => {
        // Don't trigger if clicking the link (it will trigger its own handler)
        if (e.target !== uploadLink) {
            DOM.fileInput.click();
        }
    });

    if (uploadLink) {
        uploadLink.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            DOM.fileInput.click();
        });
    }

    // File input change
    DOM.fileInput.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    });

    // Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        DOM.uploadBox.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight on drag
    ['dragenter', 'dragover'].forEach(eventName => {
        DOM.uploadBox.addEventListener(eventName, () => {
            DOM.uploadBox.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        DOM.uploadBox.addEventListener(eventName, () => {
            DOM.uploadBox.classList.remove('drag-over');
        }, false);
    });

    // Handle drop
    DOM.uploadBox.addEventListener('drop', (e) => {
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            const file = files[0];
            if (isValidFile(file)) {
                handleFileSelect(file);
            } else {
                alert('Please upload a CSV or Excel file (.csv, .xlsx)');
            }
        }
    }, false);
}

function isValidFile(file) {
    const validTypes = ['text/csv', '.csv', '.xlsx'];
    const fileName = file.name.toLowerCase();
    return validTypes.some(type => fileName.endsWith(type) || file.type.includes(type));
}

function handleFileSelect(file) {
    STATE.file = file;
    updateUploadUI(file.name);
    DOM.processBtn.disabled = false;

    // Animate file selection
    gsap.to(DOM.uploadBox, {
        scale: 0.98,
        duration: 0.2,
        yoyo: true,
        repeat: 1,
    });
}

function updateUploadUI(fileName) {
    const uploadTitle = DOM.uploadBox.querySelector('.upload-title');
    const uploadText = DOM.uploadBox.querySelector('.upload-text');

    gsap.to([uploadTitle, uploadText], {
        opacity: 0,
        duration: 0.2,
        onComplete: () => {
            uploadTitle.textContent = '✓ File Selected';
            uploadText.innerHTML = `<strong>${fileName}</strong>`;
            gsap.to([uploadTitle, uploadText], { opacity: 1, duration: 0.2 });
        },
    });
}

/* ========================================
   PROCESS HANDLING
   ======================================== */

function initializeProcessing() {
    DOM.processBtn.addEventListener('click', handleProcessClick);
}

async function handleProcessClick() {
    if (!STATE.file) return;

    STATE.processing = true;
    DOM.processBtn.classList.add('loading');
    DOM.processBtn.disabled = true;

    // Hide upload section
    gsap.to(DOM.uploadBox, { opacity: 0, duration: 0.3, pointerEvents: 'none' });

    // Show loading
    DOM.loadingContainer.style.display = 'flex';
    gsap.to(DOM.loadingContainer, { opacity: 1, duration: 0.4 });

    try {
        const response = await sendFileToAPI(STATE.file);
        STATE.sessionId = response.session_id;
        STATE.results = response.records;
        calculateSummary(response.records);

        // Start polling progress for the session; render results after completion
        if (STATE.sessionId) {
            startProgressPolling();
        } else {
            showResults();
        }
    } catch (error) {
        STATE.processing = false;
        stopProgressPolling();
        showError(error.message || 'An error occurred during processing');
        resetUI();
    }
}

async function sendFileToAPI(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('http://localhost:8000/api/process-videos/', {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        let errorMsg = `Server error: ${response.statusText}`;
        try {
            const data = await response.json();
            errorMsg = data.detail || data.message || errorMsg;
        } catch (e) {
            // Use default error message
        }
        throw new Error(errorMsg);
    }

    const data = await response.json();

    // Handle new response format: { session_id, records: [...], summary: {...} }
    if (data.session_id && data.records && Array.isArray(data.records)) {
        return data;
    }

    // Handle nested response format: { records: [...], summary: {...} }
    if (data.records && Array.isArray(data.records)) {
        return { session_id: null, ...data };
    }

    // Fallback for flat array format
    if (Array.isArray(data)) {
        return { session_id: null, records: data, summary: {} };
    }

    throw new Error('Invalid response format from server');
}

function calculateSummary(records) {
    const total = records.length;
    const success = records.filter(r => r.status === 'success').length;
    const failure = total - success;

    STATE.summary = { total, success, failure };
}

function showResults() {
    stopProgressPolling();
    STATE.processing = false;

    // Hide loading completely
    DOM.loadingContainer.style.display = 'none';
    DOM.loadingContainer.style.opacity = 0;

    // Show results cleanly
    DOM.resultsSection.style.display = 'flex';
    gsap.fromTo(
        DOM.resultsSection,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.4 }
    );

    updateSummaryDisplay();
    renderResults();
}

function startProgressPolling() {
    if (STATE.progressInterval) clearInterval(STATE.progressInterval);
    
    STATE.progressInterval = setInterval(async () => {
        if (!STATE.sessionId) return;
        
        try {
            const response = await fetch(`http://localhost:8000/api/progress/${STATE.sessionId}`);
            if (response.ok) {
                const progress = await response.json();
                updateProgressDisplay(progress);
            }
        } catch (e) {
            // Silently fail, continue polling
        }
    }, 500); // Poll every 500ms
}

function stopProgressPolling() {
    if (STATE.progressInterval) {
        clearInterval(STATE.progressInterval);
        STATE.progressInterval = null;
    }
}

function updateProgressDisplay(progress) {
    const total = progress.total_links;
    const current = progress.current_index;
    const success = progress.success_count;
    const failure = progress.failure_count;
    const message = progress.message;
    const url = progress.current_url;

    // Update loading text
    const loadingText = DOM.loadingContainer.querySelector('.loading-text');
    const loadingSubtext = DOM.loadingContainer.querySelector('.loading-subtext');

    if (loadingText) {
        loadingText.textContent = message;
    }

    if (loadingSubtext && total > 0) {
        const percent = Math.round((current / total) * 100);
        loadingSubtext.textContent = `Processing ${current}/${total} (${percent}%) | Passed: ${success} | Failed: ${failure}`;
    }

    // Update progress bar if exists
    const progressBar = DOM.loadingContainer.querySelector('.progress-bar');
    if (progressBar && total > 0) {
        const percent = (current / total) * 100;
        progressBar.style.width = percent + '%';
    }

    // Update current URL if exists
    const currentUrlEl = DOM.loadingContainer.querySelector('.current-url');
    if (currentUrlEl && url) {
        currentUrlEl.textContent = truncateUrl(url, 80);
    }

    // Stop polling if complete
    if (progress.status === 'complete') {
        stopProgressPolling();
        if (STATE.processing) {
            showResults();
        }
    }

    if (progress.status === 'error') {
        stopProgressPolling();
        if (STATE.processing) {
            showError(progress.message || 'Processing failed');
        }
    }
}

function updateSummaryDisplay() {
    const { total, success, failure } = STATE.summary;

    gsap.to(DOM.summaryTotal, {
        textContent: total,
        duration: 0.8,
        snap: { textContent: 1 },
    });

    gsap.to(DOM.summarySuccess, {
        textContent: success,
        duration: 0.8,
        snap: { textContent: 1 },
    });

    gsap.to(DOM.summaryFailure, {
        textContent: failure,
        duration: 0.8,
        snap: { textContent: 1 },
    });
}

function renderResults() {
    DOM.resultsContainer.innerHTML = '';

    STATE.results.forEach((record, index) => {
        const card = createResultCard(record);
        DOM.resultsContainer.appendChild(card);

        // Stagger animation
        gsap.from(card, {
            opacity: 0,
            x: -20,
            duration: 0.4,
            delay: index * 0.05,
        });
    });
}

function createResultCard(record) {
    const card = document.createElement('div');
    card.className = 'result-card';

    const statusClass = record.status === 'success' ? 'success' : 'failure';
    const statusIcon = record.status === 'success' ? '✓' : '✕';

    const timestamp = new Date(record.timestamp).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });

    // Build action button HTML
    let actionHTML = '';
    if (record.status === 'success' && record.download_link) {
        const href = normalizeDownloadLink(record.download_link);
        actionHTML = `
            <a href="${escapeHtml(href)}" 
               target="_blank" 
               rel="noopener noreferrer"
               class="view-btn">
                <svg class="view-btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                </svg>
                View / Download
            </a>
        `;
    } else if (record.status === 'success' && !record.download_link) {
        actionHTML = '<span class="view-btn disabled">Download unavailable</span>';
    } else {
        actionHTML = '<span class="view-btn disabled">Failed</span>';
    }

    card.innerHTML = `
        <div class="result-status ${statusClass}">${statusIcon}</div>
        <div class="result-content">
            <div class="result-url" title="${record.url}">${truncateUrl(record.url)}</div>
            <div class="result-message">${escapeHtml(record.message)}</div>
            <div class="result-time">${timestamp}</div>
        </div>
        <div class="result-action">
            ${actionHTML}
        </div>
    `;

    return card;
}

function normalizeDownloadLink(link) {
    if (typeof link !== 'string' || link.trim() === '') {
        return link;
    }

    if (link.startsWith('http://') || link.startsWith('https://')) {
        return link;
    }

    if (link.startsWith('/downloads/')) {
        return `${API_BASE}${link}`;
    }

    if (link.startsWith('downloads/')) {
        return `${API_BASE}/${link}`;
    }

    return link;
}

function truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength - 3) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ========================================
   ERROR HANDLING
   ======================================== */

function showError(message) {
    stopProgressPolling();
    STATE.processing = false;

    DOM.errorMessage.textContent = message;

    gsap.to(DOM.loadingContainer, {
        opacity: 0,
        duration: 0.2,
        pointerEvents: 'none',
        onComplete: () => {
            DOM.loadingContainer.style.display = 'none';
        },
    });
    DOM.errorContainer.style.display = 'flex';
    gsap.to(DOM.errorContainer, { opacity: 1, duration: 0.4 });
}

/* ========================================
   RESET FUNCTIONALITY
   ======================================== */

function initializeReset() {
    DOM.resetBtn.addEventListener('click', resetUI);
    DOM.errorResetBtn.addEventListener('click', resetUI);
    DOM.downloadReportBtn.addEventListener('click', downloadReport);
}

function resetUI() {
    STATE.file = null;
    STATE.processing = false;
    STATE.results = null;
    STATE.summary = null;
    STATE.sessionId = null;
    
    stopProgressPolling();

    // Hide all sections, including loading state
    gsap.to([DOM.resultsSection, DOM.errorContainer, DOM.loadingContainer], {
        opacity: 0,
        duration: 0.2,
        onComplete: () => {
            DOM.resultsSection.style.display = 'none';
            DOM.errorContainer.style.display = 'none';
            DOM.loadingContainer.style.display = 'none';
        },
    });

    // Reset upload box
    DOM.fileInput.value = '';
    const uploadTitle = DOM.uploadBox.querySelector('.upload-title');
    const uploadText = DOM.uploadBox.querySelector('.upload-text');

    uploadTitle.textContent = 'Drop your file here';
    uploadText.innerHTML = 'or <span class="upload-link">click to browse</span>';

    // Show upload box
    gsap.to(DOM.uploadBox, {
        opacity: 1,
        duration: 0.3,
        pointerEvents: 'auto',
    });

    // Reset button
    DOM.processBtn.classList.remove('loading');
    DOM.processBtn.disabled = true;
}

/* ========================================
   DOWNLOAD REPORT
   ======================================== */

function downloadReport() {
    fetch('http://localhost:8000/api/download-report')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to download report');
            }
            return response.text();
        })
        .then(reportText => {
            const blob = new Blob([reportText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'processing_report.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            alert('Error downloading report: ' + error.message);
        });
}

/* ========================================
   INITIALIZATION
   ======================================== */

function init() {
    // Initial page animation
    gsap.set(['.header', '.upload-section', '.button-section'], { opacity: 0, y: 20 });
    gsap.to(['.header', '.upload-section', '.button-section'], {
        opacity: 1,
        y: 0,
        duration: 0.6,
        stagger: 0.1,
        ease: 'power2.out',
    });

    initializeUpload();
    initializeProcessing();
    initializeReset();
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

/* ========================================
   UTILITY: DRAG OVER STYLING
   ======================================== */

const style = document.createElement('style');
style.textContent = `
    .upload-box.drag-over {
        background: rgba(99, 102, 241, 0.15) !important;
        border-color: var(--primary) !important;
        transform: translateY(-4px) scale(1.02);
    }
`;
document.head.appendChild(style);
