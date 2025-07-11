// VIN page functionality
let selectedPlates = [];

// DOM elements
const selectAllCheckbox = document.getElementById('select-all-checkbox');
const selectAllButton = document.getElementById('select-all');
const selectNoneButton = document.getElementById('select-none');
const selectMissingButton = document.getElementById('select-missing');
const selectWithVinButton = document.getElementById('select-with-vin');
const lookupButton = document.getElementById('lookup-button');
const clearButton = document.getElementById('clear-button');
const clearAllButton = document.getElementById('clear-all-button');
const selectedCountElement = document.getElementById('selected-count');
const clearCountElement = document.getElementById('clear-count');
const searchInput = document.getElementById('search');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const vinModal = document.getElementById('vin-modal');
const vinModalBody = document.getElementById('vin-modal-body');

// Initialize page
function initializePage() {
    setupEventListeners();
    updateSelectedCount();
    setupSearch();
}

function setupEventListeners() {
    // Select all checkbox in header
    selectAllCheckbox.addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('.plate-checkbox:not(:disabled)');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        updateSelectedPlates();
    });

    // Control buttons
    selectAllButton.addEventListener('click', () => selectPlates('all'));
    selectNoneButton.addEventListener('click', () => selectPlates('none'));
    selectMissingButton.addEventListener('click', () => selectPlates('missing'));
    selectWithVinButton.addEventListener('click', () => selectPlates('with-vin'));

    // Action buttons
    lookupButton.addEventListener('click', performVinLookup);
    clearButton.addEventListener('click', clearVinData);
    clearAllButton.addEventListener('click', clearAllVinData);

    // Individual checkboxes - use event delegation for dynamic content
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('plate-checkbox')) {
            updateSelectedPlates();
        }
    });

    // State override dropdowns - use event delegation
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('state-override')) {
            handleStateOverride(e);
        }
    });

    // View VIN buttons - use event delegation
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('view-vin-button')) {
            showVinData(e);
        }
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    vinModal.addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
}

function handleStateOverride(event) {
    const select = event.target;
    const plateNumber = select.dataset.plate;
    const newState = select.value;
    
    // Update the corresponding checkbox data
    const checkbox = document.querySelector(`input.plate-checkbox[data-plate="${plateNumber}"]`);
    if (checkbox) {
        checkbox.dataset.state = newState;
        
        // Update the row's data attribute
        const row = checkbox.closest('tr');
        if (row) {
            row.dataset.state = newState;
        }
        
        // If this plate is currently selected, update the selected plates array
        if (checkbox.checked) {
            updateSelectedPlates();
        }
        
        // Visual feedback
        select.style.background = '#e6fffa';
        select.style.borderColor = '#38a169';
        setTimeout(() => {
            select.style.background = '';
            select.style.borderColor = '';
        }, 1000);
    }
}

function selectPlates(type) {
    const checkboxes = document.querySelectorAll('.plate-checkbox');
    
    checkboxes.forEach(checkbox => {
        const row = checkbox.closest('tr');
        const hasVinData = row.querySelector('.status-complete') !== null;
        
        switch(type) {
            case 'all':
                checkbox.checked = !checkbox.disabled;
                break;
            case 'none':
                checkbox.checked = false;
                break;
            case 'missing':
                checkbox.checked = !checkbox.disabled && !hasVinData;
                break;
            case 'with-vin':
                checkbox.checked = !checkbox.disabled && hasVinData;
                break;
        }
    });
    
    updateSelectedPlates();
}

function updateSelectedPlates() {
    selectedPlates = [];
    const platesWithVin = [];
    
    document.querySelectorAll('.plate-checkbox:checked').forEach(checkbox => {
        const plateData = {
            license_plate: checkbox.dataset.plate,
            state: checkbox.dataset.state,
            confidence: parseFloat(checkbox.dataset.confidence),
            camera_id: checkbox.dataset.cameraId,
            timestamp: checkbox.dataset.timestamp,
            original_region: checkbox.dataset.originalRegion,
            image_filename: checkbox.dataset.image
        };
        
        selectedPlates.push(plateData);
        
        // Check if this plate has VIN data
        const row = checkbox.closest('tr');
        const hasVinData = row.querySelector('.status-complete') !== null;
        if (hasVinData) {
            platesWithVin.push(plateData);
        }
    });
    
    updateSelectedCount();
    updateClearCount(platesWithVin.length);
    updateLookupButton();
    updateClearButton(platesWithVin.length);
    updateSelectAllCheckbox();
}

function updateSelectAllCheckbox() {
    const allCheckboxes = document.querySelectorAll('.plate-checkbox:not(:disabled)');
    const checkedCheckboxes = document.querySelectorAll('.plate-checkbox:not(:disabled):checked');
    
    if (allCheckboxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length === allCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedCheckboxes.length > 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    }
}

function updateSelectedCount() {
    selectedCountElement.textContent = selectedPlates.length;
}

function updateClearCount(count) {
    clearCountElement.textContent = count;
}

function updateLookupButton() {
    const hasSelection = selectedPlates.length > 0;
    lookupButton.disabled = !hasSelection;
    lookupButton.style.opacity = hasSelection ? '1' : '0.6';
}

function updateClearButton(countWithVin) {
    const hasVinData = countWithVin > 0;
    clearButton.disabled = !hasVinData;
    clearButton.style.opacity = hasVinData ? '1' : '0.6';
}

function setupSearch() {
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const rows = document.querySelectorAll('.plate-row');
        
        rows.forEach(row => {
            const plate = row.dataset.plate.toLowerCase();
            const state = row.dataset.state.toLowerCase();
            const visible = plate.includes(searchTerm) || state.includes(searchTerm);
            row.style.display = visible ? '' : 'none';
        });
    });
}

async function performVinLookup() {
    if (selectedPlates.length === 0) return;
    
    // Disable button and show progress
    lookupButton.disabled = true;
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = `Processing ${selectedPlates.length} plates...`;
    
    try {
        const response = await fetch('/api/vin/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                plates: selectedPlates
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Update progress to 100%
        progressFill.style.width = '100%';
        progressText.textContent = `Completed! ${result.new_lookups} new lookups, ${result.total_results} total results`;
        
        // Update the UI for processed plates instead of reloading
        updatePlateRows(result.processed_plates || selectedPlates);
        
        // Clear selections and update counts
        document.querySelectorAll('.plate-checkbox:checked').forEach(checkbox => {
            checkbox.checked = false;
        });
        updateSelectedPlates();
        
        // Show success message
        showNotification(`VIN lookup completed successfully! ${result.new_lookups} new lookups performed.`, 'success');
        
    } catch (error) {
        console.error('Error performing VIN lookup:', error);
        progressText.textContent = 'Error occurred during lookup';
        showNotification('Error performing VIN lookup: ' + error.message, 'error');
    } finally {
        // Hide progress after a delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
            lookupButton.disabled = false;
        }, 3000);
    }
}

async function clearVinData() {
    // Get selected plates that have VIN data
    const platesToClear = [];
    
    document.querySelectorAll('.plate-checkbox:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        const hasVinData = row.querySelector('.status-complete') !== null;
        
        if (hasVinData) {
            platesToClear.push({
                license_plate: checkbox.dataset.plate,
                state: checkbox.dataset.state
            });
        }
    });
    
    if (platesToClear.length === 0) {
        showNotification('No plates with VIN data selected for clearing', 'warning');
        return;
    }
    
    if (!confirm(`Are you sure you want to clear VIN data for ${platesToClear.length} plates? This action cannot be undone.`)) {
        return;
    }
    
    try {
        clearButton.disabled = true;
        clearButton.textContent = '🗑️ Clearing...';
        
        const response = await fetch('/api/vin/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ plates: platesToClear })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(`Successfully cleared VIN data for ${result.cleared_count} plates`, 'success');
            
            // Update the UI for cleared plates instead of reloading
            updatePlateRowsForClearing(platesToClear);
            
            // Clear selections and update counts
            document.querySelectorAll('.plate-checkbox:checked').forEach(checkbox => {
                checkbox.checked = false;
            });
            updateSelectedPlates();
            
        } else {
            showNotification(result.error || 'Failed to clear VIN data', 'error');
        }
        
    } catch (error) {
        console.error('Error clearing VIN data:', error);
        showNotification('Error clearing VIN data. Please try again.', 'error');
    } finally {
        clearButton.disabled = false;
        clearButton.innerHTML = '🗑️ Clear Selected VIN Data (<span id="clear-count">0</span>)';
        // Re-bind the clear count element
        clearCountElement = document.getElementById('clear-count');
    }
}

async function clearAllVinData() {
    if (!confirm('Are you sure you want to clear ALL VIN data? This will remove all VIN lookup results and cannot be undone.')) {
        return;
    }
    
    if (!confirm('This will permanently delete all VIN lookup data. Are you absolutely sure?')) {
        return;
    }
    
    try {
        clearAllButton.disabled = true;
        clearAllButton.textContent = '🗑️ Clearing All...';
        
        const response = await fetch('/api/vin/clear_all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('Successfully cleared all VIN data', 'success');
            
            // Update all rows to show no VIN data instead of reloading
            document.querySelectorAll('.plate-row').forEach(row => {
                updateRowForClearingVin(row);
            });
            
            // Clear all selections and update counts
            document.querySelectorAll('.plate-checkbox:checked').forEach(checkbox => {
                checkbox.checked = false;
            });
            updateSelectedPlates();
            
        } else {
            showNotification(result.error || 'Failed to clear all VIN data', 'error');
        }
        
    } catch (error) {
        console.error('Error clearing all VIN data:', error);
        showNotification('Error clearing all VIN data. Please try again.', 'error');
    } finally {
        clearAllButton.disabled = false;
        clearAllButton.textContent = '🗑️ Clear All VIN Data';
    }
}

// Helper functions for updating UI without page reload
function updatePlateRows(processedPlates) {
    processedPlates.forEach(plateData => {
        const row = document.querySelector(`tr.plate-row[data-plate="${plateData.license_plate}"][data-state="${plateData.state}"]`);
        if (row) {
            updateRowForVinCompletion(row);
        }
    });
}

function updatePlateRowsForClearing(clearedPlates) {
    clearedPlates.forEach(plateData => {
        const row = document.querySelector(`tr.plate-row[data-plate="${plateData.license_plate}"][data-state="${plateData.state}"]`);
        if (row) {
            updateRowForClearingVin(row);
        }
    });
}

function updateRowForVinCompletion(row) {
    // Update status column
    const statusCell = row.cells[7]; // VIN Status column
    statusCell.innerHTML = '<span class="status-badge status-complete">✓ Complete</span>';
    
    // Update actions column
    const actionsCell = row.cells[8]; // Actions column
    const plateNumber = row.dataset.plate;
    const state = row.dataset.state;
    actionsCell.innerHTML = `<button class="view-vin-button" data-plate="${plateNumber}" data-state="${state}">View VIN Data</button>`;
    
    // Re-bind the view VIN button event is handled by event delegation
    
    // Disable the checkbox since it now has VIN data
    const checkbox = row.querySelector('.plate-checkbox');
    if (checkbox) {
        checkbox.disabled = true;
        checkbox.checked = false;
    }
}

function updateRowForClearingVin(row) {
    // Update status column
    const statusCell = row.cells[7]; // VIN Status column
    statusCell.innerHTML = '<span class="status-badge status-pending">⏳ Pending</span>';
    
    // Update actions column
    const actionsCell = row.cells[8]; // Actions column
    actionsCell.innerHTML = '<span class="no-data">No data</span>';
    
    // Enable the checkbox since VIN data is cleared
    const checkbox = row.querySelector('.plate-checkbox');
    if (checkbox) {
        checkbox.disabled = false;
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add CSS if not already present
    if (!document.querySelector('#notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 16px;
                border-radius: 4px;
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 12px;
                max-width: 400px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                animation: slideIn 0.3s ease-out;
            }
            .notification-success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .notification-error {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            .notification-warning {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
            }
            .notification-info {
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
                color: #0c5460;
            }
            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                opacity: 0.7;
            }
            .notification-close:hover {
                opacity: 1;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); }
                to { transform: translateX(0); }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// VIN data modal functions
function showVinData(event) {
    const button = event.target;
    const plateNumber = button.dataset.plate;
    const state = button.dataset.state;
    
    // Show loading state
    vinModalBody.innerHTML = '<div class="loading">Loading VIN data...</div>';
    vinModal.style.display = 'flex';
    
    // Fetch VIN data for this plate
    fetch(`/api/vin/data?plate=${encodeURIComponent(plateNumber)}&state=${encodeURIComponent(state)}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayVinData(data.vin_data, plateNumber);
            } else {
                vinModalBody.innerHTML = `<div class="error">Failed to load VIN data: ${data.error || 'Unknown error'}</div>`;
            }
        })
        .catch(error => {
            console.error('Error fetching VIN data:', error);
            vinModalBody.innerHTML = '<div class="error">Error loading VIN data. Please try again.</div>';
        });
}

function displayVinData(vinData, plateNumber) {
    if (!vinData) {
        vinModalBody.innerHTML = '<div class="no-data">No VIN data available for this plate.</div>';
        return;
    }
    
    let html = `
        <div class="vin-modal-header">
            <h3>🚗 Vehicle Information</h3>
            <div class="plate-badge">License Plate: ${plateNumber}</div>
        </div>
    `;
    
    // Check if we have VIN lookup results
    if (vinData.vin_lookup && vinData.vin_lookup.success && vinData.vin_lookup.vin) {
        const vehicle = vinData.vin_lookup.vin;
        
        html += `
            <div class="vin-sections">
                <div class="vin-section vehicle-info">
                    <h4>🔍 Vehicle Details</h4>
                    <div class="vin-grid">
                        <div class="vin-field primary">
                            <label>VIN:</label>
                            <span class="vin-number">${vehicle.vin || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Vehicle:</label>
                            <span>${vehicle.name || `${vehicle.year || ''} ${vehicle.make || ''} ${vehicle.model || ''}`.trim() || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Year:</label>
                            <span>${vehicle.year || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Make:</label>
                            <span>${vehicle.make || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Model:</label>
                            <span>${vehicle.model || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Trim:</label>
                            <span>${vehicle.trim || 'N/A'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="vin-section technical-info">
                    <h4>⚙️ Technical Specifications</h4>
                    <div class="vin-grid">
                        <div class="vin-field">
                            <label>Engine:</label>
                            <span>${vehicle.engine || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Style:</label>
                            <span>${vehicle.style || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Transmission:</label>
                            <span>${vehicle.transmission || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Drive Type:</label>
                            <span>${vehicle.driveType || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Fuel Type:</label>
                            <span>${vehicle.fuel || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>GVWR:</label>
                            <span>${vehicle.GVWR || 'N/A'}</span>
                        </div>
                        ${vehicle.color ? `
                        <div class="vin-field">
                            <label>Color:</label>
                            <span>${vehicle.color.name || 'Unknown'}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="vin-section detection-info">
                    <h4>📊 Detection Information</h4>
                    <div class="vin-grid">
                        <div class="vin-field">
                            <label>State:</label>
                            <span>${vinData.state || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Confidence:</label>
                            <span>${vinData.confidence ? vinData.confidence.toFixed(1) + '%' : 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Camera ID:</label>
                            <span>${vinData.camera_id || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Original Region:</label>
                            <span>${vinData.original_region || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Detection Time:</label>
                            <span>${vinData.timestamp ? new Date(vinData.timestamp).toLocaleString() : 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Lookup Time:</label>
                            <span>${vinData.lookup_timestamp ? new Date(vinData.lookup_timestamp).toLocaleString() : 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else if (vinData.vin_lookup && !vinData.vin_lookup.success) {
        html += `
            <div class="vin-sections">
                <div class="vin-section error-info">
                    <h4>❌ VIN Lookup Failed</h4>
                    <p>VIN lookup was unsuccessful for this plate.</p>
                    ${vinData.vin_lookup.error ? `<p class="error-message">Error: ${vinData.vin_lookup.error}</p>` : ''}
                </div>
                
                <div class="vin-section detection-info">
                    <h4>📊 Detection Information</h4>
                    <div class="vin-grid">
                        <div class="vin-field">
                            <label>State:</label>
                            <span>${vinData.state || 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Confidence:</label>
                            <span>${vinData.confidence ? vinData.confidence.toFixed(1) + '%' : 'N/A'}</span>
                        </div>
                        <div class="vin-field">
                            <label>Detection Time:</label>
                            <span>${vinData.timestamp ? new Date(vinData.timestamp).toLocaleString() : 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        // Fallback for other data structures
        html += '<div class="vin-details">';
        for (const [key, value] of Object.entries(vinData)) {
            if (value !== null && value !== undefined && value !== '' && typeof value !== 'object') {
                html += `<div class="vin-field">
                    <label>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                    <span>${value}</span>
                </div>`;
            }
        }
        html += '</div>';
    }
    
    vinModalBody.innerHTML = html;
}

function closeModal() {
    vinModal.style.display = 'none';
    vinModalBody.innerHTML = '';
}

// Image modal functions
function showImageModal(filename, plateNumber) {
    const imageModal = document.getElementById('image-modal');
    const modalImage = document.getElementById('modal-image');
    const modalTitle = document.getElementById('image-modal-title');
    
    modalImage.src = `/plates/${filename}`;
    modalTitle.textContent = `License Plate: ${plateNumber}`;
    imageModal.style.display = 'flex';
}

function closeImageModal() {
    const imageModal = document.getElementById('image-modal');
    imageModal.style.display = 'none';
}

// Add keyboard support for image modal
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeImageModal();
        closeModal();
    }
});

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initializePage);
