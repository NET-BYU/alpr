from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime
import os
import base64

app = Flask(__name__)

# Output files
raw_output_file = 'alpr_raw_data.jsonl'
parsed_output_file = 'alpr_parsed_data.jsonl'
event_log_file = 'event.log'
plates_dir = 'plates'

# Create plates directory if it doesn't exist
if not os.path.exists(plates_dir):
    os.makedirs(plates_dir)

def log_event(message):
    """Log events to the event log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(event_log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def save_plate_image(data):
    """Extract and save plate crop JPEG from ALPR data"""
    try:
        best_plate = data.get('best_plate', {})
        plate_crop_jpeg = best_plate.get('plate_crop_jpeg')
        
        if not plate_crop_jpeg:
            return None
        
        # Extract plate info for filename
        plate_number = best_plate.get('plate', 'UNKNOWN')
        confidence = best_plate.get('confidence', 0)
        region = best_plate.get('region', 'unknown')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Create a safe filename
        safe_plate = "".join(c for c in plate_number if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_region = region.replace('-', '_')
        
        # Parse timestamp for filename
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y%m%d_%H%M%S')
        except:
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"{safe_plate}_{safe_region}_{time_str}_{confidence:.1f}.jpg"
        filepath = os.path.join(plates_dir, filename)
        
        # Decode base64 and save as JPEG
        jpeg_data = base64.b64decode(plate_crop_jpeg)
        
        with open(filepath, 'wb') as img_file:
            img_file.write(jpeg_data)
        
        return filename
        
    except Exception as e:
        log_event(f"Error saving plate image: {e}")
        return None

def parse_license_plate_data(data):
    """Parse ALPR group data and extract useful license plate information"""
    try:
        # Extract useful information
        parsed_data = {
            'timestamp': data.get('timestamp'),
            'license_plate': data.get('best_plate', {}).get('plate'),
            'confidence': data.get('best_plate', {}).get('confidence'),
            'state_region': data.get('best_plate', {}).get('region'),
            'region_confidence': data.get('best_plate', {}).get('region_confidence'),
            'camera_id': data.get('camera_id'),
            'processing_time_ms': data.get('best_plate', {}).get('processing_time_ms'),
            'coordinates': data.get('best_plate', {}).get('coordinates'),
            'travel_direction': data.get('travel_direction'),
            'is_parked': data.get('is_parked'),
            'vehicle_info': {
                'color': data.get('vehicle', {}).get('color', [{}])[0].get('name') if data.get('vehicle', {}).get('color') else None,
                'color_confidence': data.get('vehicle', {}).get('color', [{}])[0].get('confidence') if data.get('vehicle', {}).get('color') else None,
                'make': data.get('vehicle', {}).get('make', [{}])[0].get('name') if data.get('vehicle', {}).get('make') else None,
                'make_confidence': data.get('vehicle', {}).get('make', [{}])[0].get('confidence') if data.get('vehicle', {}).get('make') else None,
                'body_type': data.get('vehicle', {}).get('body_type', [{}])[0].get('name') if data.get('vehicle', {}).get('body_type') else None,
                'year_range': data.get('vehicle', {}).get('year', [{}])[0].get('name') if data.get('vehicle', {}).get('year') else None
            },
            'uuid': data.get('best_uuid')
        }
        return parsed_data
    except Exception as e:
        log_event(f"Error parsing license plate data: {e}")
        return None

@app.route('/alpr', methods=['POST'])
def receive_alpr_data():
    try:
        # Get JSON data from the POST request
        json_data = request.get_json()
        
        if json_data is None:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Add timestamp to the data if not present
        if 'timestamp' not in json_data:
            json_data['timestamp'] = datetime.now().isoformat()
        
        # Save raw data
        with open(raw_output_file, 'a') as f:
            f.write(json.dumps(json_data) + '\n')
        
        # Process based on data type
        data_type = json_data.get('data_type', 'unknown')
        
        if data_type == 'heartbeat':
            # Extract heartbeat stats
            video_streams = json_data.get('video_streams', [])
            total_plate_reads = sum(stream.get('total_plate_reads', 0) for stream in video_streams)
            
            # Find the most recent plate read timestamp
            last_plate_read = 0
            for stream in video_streams:
                if stream.get('last_plate_read', 0) > last_plate_read:
                    last_plate_read = stream.get('last_plate_read', 0)
            
            # Convert epoch timestamp to readable format
            last_plate_time = "Never"
            if last_plate_read > 0:
                try:
                    last_plate_time = datetime.fromtimestamp(last_plate_read / 1000).strftime('%H:%M:%S')
                except:
                    last_plate_time = "Unknown"
            
            log_event(f"heartbeat - Total plates read: {total_plate_reads}, Last plate read: {last_plate_time}")
            
        elif data_type == 'alpr_group':
            # Parse license plate data
            parsed_data = parse_license_plate_data(json_data)
            
            if parsed_data and parsed_data.get('license_plate'):
                # Save plate image
                image_filename = save_plate_image(json_data)
                
                # Add image filename to parsed data
                if image_filename:
                    parsed_data['image_filename'] = image_filename
                
                # Save parsed data
                with open(parsed_output_file, 'a') as f:
                    f.write(json.dumps(parsed_data) + '\n')
                
                # Log license plate event
                plate = parsed_data['license_plate']
                state = parsed_data['state_region'] or 'Unknown'
                timestamp = parsed_data['timestamp'] or 'Unknown'
                confidence = parsed_data.get('confidence', 0)
                
                image_msg = f" (Image: {image_filename})" if image_filename else ""
                log_event(f"LICENSE PLATE - {plate} ({state}) at {timestamp} - {confidence:.1f}% confidence{image_msg}")
            else:
                log_event("alpr_group received but no valid license plate data found")
        else:
            log_event(f"Received data type: {data_type}")
        
        # Return success response
        return jsonify({'status': 'success', 'message': 'Data received and processed'}), 200
        
    except Exception as e:
        error_msg = f"Error processing request: {e}"
        log_event(error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Display ALPR dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/plates')
def get_plates():
    """API endpoint to get all plate data"""
    plates = []
    try:
        if os.path.exists(parsed_output_file):
            with open(parsed_output_file, 'r') as f:
                for line in f:
                    try:
                        plate_data = json.loads(line.strip())
                        plates.append(plate_data)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(plates)

@app.route('/api/events')
def get_recent_events():
    """API endpoint to get recent events from log"""
    events = []
    try:
        if os.path.exists(event_log_file):
            with open(event_log_file, 'r') as f:
                lines = f.readlines()
                # Get last 10 events
                recent_lines = lines[-10:] if len(lines) > 10 else lines
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        events.append(line)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(events)

@app.route('/plates/<filename>')
def serve_plate_image(filename):
    """Serve plate images"""
    from flask import send_from_directory
    return send_from_directory(plates_dir, filename)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get basic statistics about processed data"""
    try:
        # Count lines in files
        raw_count = 0
        parsed_count = 0
        
        if os.path.exists(raw_output_file):
            with open(raw_output_file, 'r') as f:
                raw_count = sum(1 for line in f)
        
        if os.path.exists(parsed_output_file):
            with open(parsed_output_file, 'r') as f:
                parsed_count = sum(1 for line in f)
        
        # Count plate images
        image_count = 0
        if os.path.exists(plates_dir):
            image_count = len([f for f in os.listdir(plates_dir) if f.endswith('.jpg')])
        
        return jsonify({
            'raw_records': raw_count,
            'parsed_plates': parsed_count,
            'plate_images': image_count,
            'files': {
                'raw_data': raw_output_file,
                'parsed_data': parsed_output_file,
                'event_log': event_log_file,
                'plates_directory': plates_dir
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Dashboard HTML Template
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ALPR Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .controls {
            padding: 20px 30px;
            background: #f7fafc;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .control-group label {
            font-weight: 600;
            color: #4a5568;
        }
        
        select, input {
            padding: 8px 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 20px 30px;
            background: #f7fafc;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #718096;
            margin-top: 5px;
        }
        
        .table-container {
            padding: 30px;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        }
        
        th {
            background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        th:hover {
            background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        }
        
        th.sortable::after {
            content: ' ↕';
            opacity: 0.5;
        }
        
        th.sort-asc::after {
            content: ' ↑';
            opacity: 1;
        }
        
        th.sort-desc::after {
            content: ' ↓';
            opacity: 1;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        tr:hover {
            background-color: #f7fafc;
        }
        
        .plate-number {
            font-weight: bold;
            font-size: 1.1em;
            color: #2d3748;
            background: #edf2f7;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
        }
        
        .region {
            background: #bee3f8;
            color: #2b6cb0;
            padding: 3px 8px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: 500;
            cursor: help;
            position: relative;
        }
        
        .region:hover::after {
            content: attr(data-confidence);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #2d3748;
            color: white;
            padding: 5px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
            margin-bottom: 5px;
        }
        
        .region:hover::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 5px solid transparent;
            border-top-color: #2d3748;
            margin-bottom: -5px;
        }
        
        .confidence {
            font-weight: bold;
        }
        
        .confidence.high { color: #38a169; }
        .confidence.medium { color: #d69e2e; }
        .confidence.low { color: #e53e3e; }
        
        .timestamp {
            font-family: monospace;
            color: #4a5568;
        }
        
        .vehicle-info {
            font-size: 0.9em;
            color: #718096;
        }
        
        .plate-image {
            max-width: 80px;
            max-height: 40px;
            border-radius: 5px;
            cursor: pointer;
            transition: transform 0.3s;
        }
        
        .plate-image:hover {
            transform: scale(2);
            z-index: 1000;
            position: relative;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #38a169;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
            max-width: 400px;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.heartbeat {
            background: #3182ce;
        }
        
        .notification.error {
            background: #e53e3e;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
        
        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .control-group {
                justify-content: space-between;
            }
            
            table {
                font-size: 0.9em;
            }
            
            .plate-image:hover {
                transform: scale(1.5);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 ALPR Dashboard</h1>
            <p>Real-time License Plate Recognition System</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="total-plates">-</div>
                <div class="stat-label">Total Plates</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avg-confidence">-</div>
                <div class="stat-label">Avg Confidence</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="last-detection">-</div>
                <div class="stat-label">Last Detection</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="unique-states">-</div>
                <div class="stat-label">Unique States</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="sort-by">Sort by:</label>
                <select id="sort-by">
                    <option value="timestamp">Timestamp</option>
                    <option value="license_plate">Plate Number</option>
                    <option value="state_region">Region</option>
                    <option value="confidence">Confidence</option>
                </select>
            </div>
            <div class="control-group">
                <label for="filter-region">Filter Region:</label>
                <select id="filter-region">
                    <option value="">All Regions</option>
                </select>
            </div>
            <div class="control-group">
                <label for="search">Search:</label>
                <input type="text" id="search" placeholder="Search plates...">
            </div>
            <div class="control-group">
                <label>
                    <input type="checkbox" id="auto-refresh" checked> Auto-refresh
                </label>
            </div>
        </div>
        
        <div class="table-container">
            <div id="loading" class="loading">Loading data...</div>
            <table id="plates-table" style="display: none;">
                <thead>
                    <tr>
                        <th class="sortable" data-column="license_plate">Plate #</th>
                        <th class="sortable" data-column="state_region">Region</th>
                        <th class="sortable" data-column="confidence">Confidence</th>
                        <th class="sortable" data-column="timestamp">Timestamp</th>
                        <th class="sortable" data-column="vehicle_info.make">Make</th>
                        <th class="sortable" data-column="vehicle_info.color">Color</th>
                        <th>Image</th>
                    </tr>
                </thead>
                <tbody id="plates-tbody">
                </tbody>
            </table>
            <div id="no-data" class="no-data" style="display: none;">
                No license plate data available
            </div>
        </div>
    </div>

    <script>
        let platesData = [];
        let sortColumn = 'timestamp';
        let sortDirection = 'desc';
        let lastEventCount = 0;
        
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
            
            const totalPlates = platesData.length;
            const avgConfidence = (platesData.reduce((sum, plate) => sum + (plate.confidence || 0), 0) / totalPlates).toFixed(1);
            const lastDetection = platesData.length > 0 ? 
                new Date(platesData[platesData.length - 1].timestamp).toLocaleTimeString() : 'None';
            const uniqueStates = new Set(platesData.map(plate => plate.state_region)).size;
            
            document.getElementById('total-plates').textContent = totalPlates;
            document.getElementById('avg-confidence').textContent = avgConfidence + '%';
            document.getElementById('last-detection').textContent = lastDetection;
            document.getElementById('unique-states').textContent = uniqueStates;
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
            
            platesData.sort((a, b) => {
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
            
            let filteredData = platesData.filter(plate => {
                const matchesRegion = !regionFilter || plate.state_region === regionFilter;
                const matchesSearch = !searchTerm || 
                    plate.license_plate?.toLowerCase().includes(searchTerm) ||
                    plate.state_region?.toLowerCase().includes(searchTerm) ||
                    plate.vehicle_info?.make?.toLowerCase().includes(searchTerm) ||
                    plate.vehicle_info?.color?.toLowerCase().includes(searchTerm);
                
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
                
                const make = plate.vehicle_info?.make || 'Unknown';
                const color = plate.vehicle_info?.color || 'Unknown';
                
                row.innerHTML = `
                    <td><span class="plate-number">${plate.license_plate || 'Unknown'}</span></td>
                    <td><span class="region" data-confidence="Region Confidence: ${(plate.region_confidence || 0).toFixed(1)}%">${plate.state_region || 'Unknown'}</span></td>
                    <td><span class="confidence ${confidenceClass}">${(plate.confidence || 0).toFixed(1)}%</span></td>
                    <td><span class="timestamp">${timestamp}</span></td>
                    <td><span class="vehicle-info">${make}</span></td>
                    <td><span class="vehicle-info">${color}</span></td>
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
        fetchPlates();
        startAutoRefresh();
        
        // Initial sort by timestamp (newest first)
        setTimeout(() => {
            sortData('timestamp');
        }, 500);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Initialize log file
    log_event("ALPR Integrated Server starting up...")
    log_event(f"Raw data will be saved to: {os.path.abspath(raw_output_file)}")
    log_event(f"Parsed data will be saved to: {os.path.abspath(parsed_output_file)}")
    log_event(f"Event log: {os.path.abspath(event_log_file)}")
    log_event(f"Plate images will be saved to: {os.path.abspath(plates_dir)}")
    log_event(f"Configure openALPR to POST to: http://localhost:5000/alpr")
    log_event("Server ready to receive data...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)