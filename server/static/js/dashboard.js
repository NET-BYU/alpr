let platesData = [];
let sortColumn = 'timestamp';
let sortDirection = 'desc';
let lastEventCount = 0;

// Camera management - support both HTTP and RTSP cameras
let allCameras = [];
let currentCameraIndex = 0;

// Initialize camera list from server data
function initializeCameras() {
    allCameras = [];
    
    // Add HTTP cameras
    if (cameraData.http_cameras) {
        cameraData.http_cameras.forEach((ip, index) => {
            allCameras.push({
                ip: ip,
                type: 'http',
                port: 8080,
                index: allCameras.length,
                display_name: `HTTP Camera ${index + 1} (${ip})`
            });
        });
    }
    
    // Add RTSP cameras
    if (cameraData.rtsp_cameras) {
        cameraData.rtsp_cameras.forEach((camera, index) => {
            const ip = camera.ip || camera; // Handle both object and string formats
            const rtspUrl = camera.rtsp_url || `rtsp://${ip}:554/`;
            
            allCameras.push({
                ip: ip,
                type: 'rtsp',
                port: 554,
                rtsp_url: rtspUrl,
                username: camera.username || null,
                password: camera.password || null,
                index: allCameras.length,
                display_name: `RTSP Camera ${index + 1} (${ip})`
            });
        });
    }
    
    // Fallback to legacy camera list if no new format
    if (allCameras.length === 0 && cameraIPs && cameraIPs.length > 0) {
        cameraIPs.forEach((ip, index) => {
            allCameras.push({
                ip: ip,
                type: 'http',
                port: 8080,
                index: allCameras.length,
                display_name: `Camera ${index + 1} (${ip})`
            });
        });
    }
}

// Camera functions
function switchCamera(direction) {
    currentCameraIndex += direction;
    
    if (currentCameraIndex < 0) {
        currentCameraIndex = allCameras.length - 1;
    } else if (currentCameraIndex >= allCameras.length) {
        currentCameraIndex = 0;
    }
    
    loadCurrentCamera();
    updateCameraControls();
}

function loadCurrentCamera() {
    const videoStream = document.getElementById('video-stream');
    const videoError = document.getElementById('video-error');
    const cameraStatus = document.getElementById('camera-status');
    const videoInfo = document.getElementById('video-info');
    
    if (allCameras.length === 0) {
        videoError.innerHTML = '<div>📹 No cameras configured<br><small>Add camera IPs to the server configuration</small></div>';
        cameraStatus.classList.remove('online');
        return;
    }
    
    const currentCamera = allCameras[currentCameraIndex];
    let streamUrl;
    
    // Create appropriate stream URL based on camera type
    if (currentCamera.type === 'rtsp') {
        // For RTSP cameras, we'll try to use an HTTP preview if available
        // Otherwise show RTSP info (browsers can't directly display RTSP)
        streamUrl = `http://${currentCamera.ip}:8080`; // Fallback to HTTP preview
    } else {
        // HTTP cameras
        streamUrl = `http://${currentCamera.ip}:${currentCamera.port}`;
    }
    
    // Update info
    let displayInfo = `${currentCamera.display_name} (${currentCameraIndex + 1}/${allCameras.length})`;
    if (currentCamera.type === 'rtsp') {
        displayInfo += `\nRTSP: ${currentCamera.rtsp_url}`;
    }
    videoInfo.textContent = displayInfo;
    
    // Show loading state
    videoError.innerHTML = '<div>📹 Connecting to camera...<br><small>Loading stream</small></div>';
    videoError.style.display = 'flex';
    videoStream.style.display = 'none';
    cameraStatus.classList.remove('online');
    
    if (currentCamera.type === 'rtsp') {
        // For RTSP cameras, show special message
        videoError.innerHTML = `<div>📹 RTSP Camera<br><small>${currentCamera.display_name}<br>RTSP: ${currentCamera.rtsp_url}<br>Attempting HTTP preview...</small></div>`;
    }
    
    // Test if camera is accessible
    const testImg = new Image();
    testImg.onload = function() {
        // Camera is accessible, switch to video stream
        videoStream.src = streamUrl;
        videoStream.onload = function() {
            videoStream.style.display = 'block';
            videoError.style.display = 'none';
            cameraStatus.classList.add('online');
        };
        videoStream.onerror = function() {
            showCameraError(`Failed to load stream from ${currentCamera.ip}`);
        };
    };
    testImg.onerror = function() {
        if (currentCamera.type === 'rtsp') {
            showCameraError(`RTSP Camera: ${currentCamera.rtsp_url}<br>No HTTP preview available<br>Use RTSP client to view stream`);
        } else {
            showCameraError(`Camera at ${currentCamera.ip}:${currentCamera.port} is not accessible`);
        }
    };
    testImg.src = streamUrl;
    
    // Set a timeout for connection attempt
    setTimeout(() => {
        if (!cameraStatus.classList.contains('online')) {
            showCameraError(`Connection timeout to ${currentCamera.ip}`);
        }
    }, 10000);
}

function showCameraError(message) {
    const videoError = document.getElementById('video-error');
    const cameraStatus = document.getElementById('camera-status');
    
    videoError.innerHTML = `<div>📹 Camera Offline<br><small>${message}</small></div>`;
    videoError.style.display = 'flex';
    document.getElementById('video-stream').style.display = 'none';
    cameraStatus.classList.remove('online');
}

function updateCameraControls() {
    const prevBtn = document.getElementById('prev-camera');
    const nextBtn = document.getElementById('next-camera');
    
    if (allCameras.length <= 1) {
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    } else {
        prevBtn.style.display = 'flex';
        nextBtn.style.display = 'flex';
    }
}

// Fetch and display plates data
async function fetchPlates() {
    try {
        const response = await fetch('/api/plates');
        const data = await response.json();
        platesData = data;
        updateTable();
        updateStats();
        updateRegionFilter();
    } catch (error) {
        console.error('Error fetching plates:', error);
        showNotification('Error fetching data', 'error');
    }
}

// Check for new events and show notifications
async function checkEvents() {
    try {
        const response = await fetch('/api/events');
        const events = await response.json();
        
        if (events.length > lastEventCount) {
            const newEvents = events.slice(lastEventCount);
            newEvents.forEach(event => {
                if (event.includes('LICENSE PLATE')) {
                    showNotification(event, 'license');
                } else if (event.includes('heartbeat')) {
                    showNotification(event, 'heartbeat');
                }
            });
        }
        lastEventCount = events.length;
    } catch (error) {
        console.error('Error checking events:', error);
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 100);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => document.body.removeChild(notification), 300);
    }, 4000);
}

// Update statistics
function updateStats() {
    if (platesData.length === 0) return;
    
    const groupedPlates = groupPlatesByNumber(platesData);
    const totalUniqueePlates = groupedPlates.length;
    const totalScans = platesData.length;
    const avgConfidence = (platesData.reduce((sum, plate) => sum + (plate.confidence || 0), 0) / totalScans).toFixed(1);
    const lastDetection = platesData.length > 0 ? 
        new Date(platesData[platesData.length - 1].timestamp).toLocaleTimeString() : 'None';
    const uniqueStates = new Set(platesData.map(plate => plate.state_region)).size;
    
    // Show unique plates count with total scans in parentheses
    document.getElementById('total-plates').textContent = `${totalUniqueePlates} (${totalScans})`;
    document.getElementById('avg-confidence').textContent = avgConfidence + '%';
    document.getElementById('last-detection').textContent = lastDetection;
    document.getElementById('unique-states').textContent = uniqueStates;
}

// Group plates by license plate number and keep most recent
function groupPlatesByNumber(plates) {
    const grouped = {};
    
    plates.forEach(plate => {
        const plateNumber = plate.license_plate || 'Unknown';
        
        if (!grouped[plateNumber]) {
            grouped[plateNumber] = {
                ...plate,
                timestamps: [plate.timestamp],
                scan_count: 1
            };
        } else {
            // Add timestamp to the list
            grouped[plateNumber].timestamps.push(plate.timestamp);
            grouped[plateNumber].scan_count++;
            
            // Update to most recent data if this scan is newer
            const currentTime = new Date(plate.timestamp);
            const existingTime = new Date(grouped[plateNumber].timestamp);
            
            if (currentTime > existingTime) {
                // Keep the timestamps and scan count, but update other data
                const timestamps = grouped[plateNumber].timestamps;
                const scanCount = grouped[plateNumber].scan_count;
                grouped[plateNumber] = {
                    ...plate,
                    timestamps: timestamps,
                    scan_count: scanCount
                };
            }
        }
    });
    
    // Sort timestamps for each plate (most recent first)
    Object.values(grouped).forEach(plate => {
        plate.timestamps.sort((a, b) => new Date(b) - new Date(a));
    });
    
    return Object.values(grouped);
}

// Update region filter options
function updateRegionFilter() {
    const regionSelect = document.getElementById('filter-region');
    const regions = [...new Set(platesData.map(plate => plate.state_region))].sort();
    
    // Clear existing options except "All Regions"
    regionSelect.innerHTML = '<option value="">All Regions</option>';
    
    regions.forEach(region => {
        if (region) {
            const option = document.createElement('option');
            option.value = region;
            option.textContent = region;
            regionSelect.appendChild(option);
        }
    });
}

// Get nested property value
function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current && current[key], obj);
}

// Sort data
function sortData(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'desc';
    }
    
    // Group the data first, then sort
    const groupedPlates = groupPlatesByNumber(platesData);
    
    groupedPlates.sort((a, b) => {
        let aVal = getNestedValue(a, column);
        let bVal = getNestedValue(b, column);
        
        if (column === 'timestamp') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }
        
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Update platesData with sorted grouped data for consistent behavior
    platesData = groupedPlates;
    updateTable();
    updateSortHeaders();
}

// Update sort headers
function updateSortHeaders() {
    document.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const currentTh = document.querySelector(`th[data-column="${sortColumn}"]`);
    if (currentTh) {
        currentTh.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    }
}

// Filter and update table
function updateTable() {
    const regionFilter = document.getElementById('filter-region').value;
    const searchTerm = document.getElementById('search').value.toLowerCase();
    
    // Group plates by license plate number
    const groupedPlates = groupPlatesByNumber(platesData);
    
    let filteredData = groupedPlates.filter(plate => {
        const matchesRegion = !regionFilter || plate.state_region === regionFilter;
        const matchesSearch = !searchTerm || 
            plate.license_plate?.toLowerCase().includes(searchTerm) ||
            plate.state_region?.toLowerCase().includes(searchTerm) ||
            plate.vehicle_info?.make?.toLowerCase().includes(searchTerm) ||
            plate.camera_id?.toString().toLowerCase().includes(searchTerm);
        
        return matchesRegion && matchesSearch;
    });
    
    const tbody = document.getElementById('plates-tbody');
    const table = document.getElementById('plates-table');
    const loading = document.getElementById('loading');
    const noData = document.getElementById('no-data');
    
    if (filteredData.length === 0) {
        table.style.display = 'none';
        loading.style.display = 'none';
        noData.style.display = 'block';
        return;
    }
    
    tbody.innerHTML = '';
    
    filteredData.forEach(plate => {
        const row = document.createElement('tr');
        
        const confidenceClass = plate.confidence > 90 ? 'high' : 
                              plate.confidence > 75 ? 'medium' : 'low';
        
        const timestamp = plate.timestamp ? 
            new Date(plate.timestamp).toLocaleString() : 'Unknown';
        
        // Create tooltip with all timestamps
        const allTimestamps = plate.timestamps.map(ts => 
            new Date(ts).toLocaleString()
        ).join('\n');
        
        const timestampTooltip = plate.scan_count > 1 ? 
            `Scanned ${plate.scan_count} times:\n${allTimestamps}` : 
            `Scanned once:\n${timestamp}`;
        
        const make = plate.vehicle_info?.make || 'Unknown';
        const cameraId = plate.camera_id || 'Unknown';
        
        // Add scan count indicator to plate number if scanned multiple times
        const plateDisplay = plate.scan_count > 1 ? 
            `${plate.license_plate} (${plate.scan_count}x)` : 
            plate.license_plate || 'Unknown';
        
        row.innerHTML = `
            <td><span class="plate-number ${plate.scan_count > 1 ? 'multiple-scans' : ''}">${plateDisplay}</span></td>
            <td><span class="region" data-confidence="Region Confidence: ${(plate.region_confidence || 0).toFixed(1)}%">${plate.state_region || 'Unknown'}</span></td>
            <td><span class="confidence ${confidenceClass}">${(plate.confidence || 0).toFixed(1)}%</span></td>
            <td><span class="timestamp hover-tooltip" data-tooltip="${timestampTooltip}">${timestamp}</span></td>
            <td><span class="vehicle-info">${make}</span></td>
            <td><span class="camera-id">${cameraId}</span></td>
            <td>${plate.image_filename ? 
                `<img src="/plates/${plate.image_filename}" alt="Plate" class="plate-image">` : 
                'No image'}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    table.style.display = 'table';
    loading.style.display = 'none';
    noData.style.display = 'none';
}

// Event listeners
document.getElementById('sort-by').addEventListener('change', (e) => {
    sortData(e.target.value);
});

document.getElementById('filter-region').addEventListener('change', updateTable);
document.getElementById('search').addEventListener('input', updateTable);

document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        sortData(th.dataset.column);
    });
});

// Auto-refresh functionality
function startAutoRefresh() {
    setInterval(() => {
        if (document.getElementById('auto-refresh').checked) {
            fetchPlates();
            checkEvents();
        }
    }, 3000); // Refresh every 3 seconds
}

// Initialize
initializeCameras();
fetchPlates();
startAutoRefresh();
loadCurrentCamera();
updateCameraControls();

// Initial sort by timestamp (newest first)
setTimeout(() => {
    sortData('timestamp');
}, 500);

// Refresh camera connection periodically
setInterval(() => {
    const cameraStatus = document.getElementById('camera-status');
    if (!cameraStatus.classList.contains('online')) {
        loadCurrentCamera();
    }
}, 30000); // Try to reconnect every 30 seconds
