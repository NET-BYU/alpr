// Initialize cameras array from server data
let allCameras = [];

function initializeCameras() {
    allCameras = [];
    let index = 0;
    
    // Add HTTP cameras
    if (cameraData.http_cameras) {
        cameraData.http_cameras.forEach((ip) => {
            allCameras.push({
                ip: ip,
                type: 'http',
                port: 8080,
                index: index++
            });
        });
    }
    
    // Add RTSP cameras
    if (cameraData.rtsp_cameras) {
        cameraData.rtsp_cameras.forEach((camera) => {
            const ip = camera.ip || camera; // Handle both object and string formats
            const rtspUrl = camera.rtsp_url || `rtsp://${ip}:554/`;
            
            allCameras.push({
                ip: ip,
                type: 'rtsp',
                port: 554,
                rtsp_url: rtspUrl,
                username: camera.username || null,
                password: camera.password || null,
                index: index++
            });
        });
    }
    
    // Fallback to legacy camera list if no new format
    if (allCameras.length === 0 && cameraIPs && cameraIPs.length > 0) {
        cameraIPs.forEach((ip) => {
            allCameras.push({
                ip: ip,
                type: 'http',
                port: 8080,
                index: index++
            });
        });
    }
}

function loadCamera(index) {
    if (index >= allCameras.length) return;
    
    const camera = allCameras[index];
    const videoStream = document.getElementById(`camera-stream-${index}`);
    const videoError = document.getElementById(`camera-error-${index}`);
    const cameraStatus = document.getElementById(`camera-status-${index}`);
    const cameraInfo = document.getElementById(`camera-info-${index}`);
    
    let streamUrl;
    let displayInfo;
    
    if (camera.type === 'rtsp') {
        // For RTSP cameras, try HTTP preview first
        streamUrl = `http://${camera.ip}:8080`;
        displayInfo = `RTSP Camera (${camera.rtsp_url})`;
    } else {
        // HTTP cameras
        streamUrl = `http://${camera.ip}:${camera.port}`;
        displayInfo = `HTTP Camera (${camera.ip}:${camera.port})`;
    }
    
    // Update info
    cameraInfo.textContent = displayInfo;
    
    // Show loading state
    if (camera.type === 'rtsp') {
        videoError.innerHTML = `<div>📹 RTSP Camera<br><small>RTSP: ${camera.rtsp_url}<br>Attempting HTTP preview...</small></div>`;
    } else {
        videoError.innerHTML = `<div>📹 Connecting to camera...<br><small>Loading stream from ${camera.ip}</small></div>`;
    }
    
    videoError.style.display = 'flex';
    videoStream.style.display = 'none';
    cameraStatus.classList.remove('online');
    
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
            showCameraError(index, `Failed to load stream from ${camera.ip}`);
        };
    };
    testImg.onerror = function() {
        if (camera.type === 'rtsp') {
            showCameraError(index, `RTSP Camera: ${camera.rtsp_url}<br>No HTTP preview available<br>Use RTSP client to view stream`);
        } else {
            showCameraError(index, `Camera at ${camera.ip}:${camera.port} is not accessible`);
        }
    };
    testImg.src = streamUrl;
    
    // Set a timeout for connection attempt
    setTimeout(() => {
        const status = document.getElementById(`camera-status-${index}`);
        if (!status.classList.contains('online')) {
            showCameraError(index, `Connection timeout to ${camera.ip}`);
        }
    }, 10000);
}

function showCameraError(index, message) {
    const videoError = document.getElementById(`camera-error-${index}`);
    const cameraStatus = document.getElementById(`camera-status-${index}`);
    const videoStream = document.getElementById(`camera-stream-${index}`);
    
    videoError.innerHTML = `<div>📹 Camera Offline<br><small>${message}</small></div>`;
    videoError.style.display = 'flex';
    videoStream.style.display = 'none';
    cameraStatus.classList.remove('online');
}

function loadAllCameras() {
    for (let i = 0; i < allCameras.length; i++) {
        loadCamera(i);
    }
}

function checkAllCameras() {
    for (let i = 0; i < allCameras.length; i++) {
        const cameraStatus = document.getElementById(`camera-status-${i}`);
        if (cameraStatus && !cameraStatus.classList.contains('online')) {
            loadCamera(i);
        }
    }
}

// Initialize cameras and load them
initializeCameras();
loadAllCameras();

// Refresh camera connections periodically
setInterval(() => {
    checkAllCameras();
}, 30000); // Try to reconnect every 30 seconds
