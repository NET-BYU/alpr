from flask import Flask, request, jsonify, render_template, send_from_directory
import json
from datetime import datetime
import os
import base64
import yaml
import math
import requests
from collections import defaultdict
import threading
import time

app = Flask(__name__)

# Output files
# Load configuration from config.yaml
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)['integrated_server']

raw_output_file = config.get('raw_output_file', 'alpr_raw_data.jsonl')
parsed_output_file = config.get('parsed_output_file', 'alpr_parsed_data.jsonl')
event_log_file = config.get('event_log_file', 'event.log')
plates_dir = config.get('plates_dir', 'plates')

# Camera configuration - support both new and legacy formats
HTTP_CAMERAS = config.get('http_cameras', [])
RTSP_CAMERAS_RAW = config.get('rtsp_cameras', [])
LEGACY_CAMERAS = config.get('camera_ips', [])

# Process RTSP cameras to handle both simple IPs and credential objects
RTSP_CAMERAS = []
for camera in RTSP_CAMERAS_RAW:
    if isinstance(camera, str):
        # Simple IP format
        RTSP_CAMERAS.append({
            'ip': camera,
            'username': None,
            'password': None,
            'rtsp_url': f"rtsp://{camera}:554/"
        })
    elif isinstance(camera, dict) and 'ip' in camera:
        # Object format with credentials
        ip = camera['ip']
        username = camera.get('username')
        password = camera.get('password')
        
        if username and password:
            rtsp_url = f"rtsp://{username}:{password}@{ip}:554/"
        else:
            rtsp_url = f"rtsp://{ip}:554/"
        
        RTSP_CAMERAS.append({
            'ip': ip,
            'username': username,
            'password': password,
            'rtsp_url': rtsp_url
        })

# If using legacy format, treat as HTTP cameras
if LEGACY_CAMERAS and not HTTP_CAMERAS:
    HTTP_CAMERAS = LEGACY_CAMERAS

# Create combined camera list for backward compatibility
CAMERA_IPS = HTTP_CAMERAS  # For backward compatibility with existing code

# Create plates directory if it doesn't exist
if not os.path.exists(plates_dir):
    os.makedirs(plates_dir)

# VIN lookup configuration
VIN_RESULTS_FILE = config.get('vin_results_file', 'alpr_vin_lookup.json')
VIN_API_KEY = 'ehifeCWYw8awg2G'  # Move this to config.yaml in production

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
    # Pass camera data to the template
    camera_data = {
        'http_cameras': HTTP_CAMERAS,
        'rtsp_cameras': RTSP_CAMERAS,
        'legacy_cameras': CAMERA_IPS  # For backward compatibility
    }
    return render_template('dashboard.html', 
                          camera_ips=json.dumps(CAMERA_IPS),  # Keep for backward compatibility
                          camera_data=json.dumps(camera_data))

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

@app.route('/cameras')
def cameras_grid():
    """Display all cameras in a grid view"""
    
    # Calculate grid size (nearest square) based on total cameras
    total_cameras = len(HTTP_CAMERAS) + len(RTSP_CAMERAS)
    if total_cameras == 0:
        grid_size = 1
    else:
        grid_size = math.ceil(math.sqrt(total_cameras))
    
    # Pass camera data to the template
    camera_data = {
        'http_cameras': HTTP_CAMERAS,
        'rtsp_cameras': RTSP_CAMERAS,
        'legacy_cameras': CAMERA_IPS  # For backward compatibility
    }
    
    return render_template('cameras.html', 
                          camera_ips=json.dumps(CAMERA_IPS),  # Keep for backward compatibility
                          camera_data=json.dumps(camera_data),
                          grid_size=grid_size,
                          num_cameras=total_cameras,
                          num_http=len(HTTP_CAMERAS),
                          num_rtsp=len(RTSP_CAMERAS))

@app.route('/api/vin_lookup', methods=['POST'])
def vin_lookup():
    """API endpoint to lookup VIN information"""
    try:
        # Get JSON data from the POST request
        json_data = request.get_json()
        
        if json_data is None or 'vin' not in json_data:
            return jsonify({'error': 'No VIN provided'}), 400
        
        vin = json_data['vin']
        
        # Check if already looked up
        if os.path.exists(VIN_RESULTS_FILE):
            with open(VIN_RESULTS_FILE, 'r') as f:
                results = json.load(f)
                if vin in results:
                    # Return cached result
                    return jsonify({'status': 'success', 'data': results[vin]}), 200
        
        # Call external VIN lookup service (example: vinapi.io)
        response = requests.get(f'https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json')
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant information
            if 'Results' in data and len(data['Results']) > 0:
                vehicle_data = data['Results'][0]
                
                # Save to results file
                if os.path.exists(VIN_RESULTS_FILE):
                    with open(VIN_RESULTS_FILE, 'r') as f:
                        all_results = json.load(f)
                else:
                    all_results = {}
                
                all_results[vin] = vehicle_data
                
                with open(VIN_RESULTS_FILE, 'w') as f:
                    json.dump(all_results, f, indent=4)
                
                return jsonify({'status': 'success', 'data': vehicle_data}), 200
            else:
                return jsonify({'status': 'error', 'message': 'No data found for this VIN'}), 404
        else:
            return jsonify({'status': 'error', 'message': 'Error calling VIN lookup service'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_unique_plates_from_data():
    """Get unique license plates from parsed ALPR data"""
    unique_plates = defaultdict(lambda: {'state': None, 'confidence': 0, 'camera_id': None, 'timestamp': None, 'image_filename': None})
    
    try:
        if os.path.exists(parsed_output_file):
            with open(parsed_output_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        license_plate = data.get('license_plate')
                        state_region = data.get('state_region')
                        confidence = data.get('confidence', 0)
                        camera_id = data.get('camera_id')
                        timestamp = data.get('timestamp')
                        image_filename = data.get('image_filename')
                        
                        if license_plate and state_region:
                            # Extract state code from region (e.g., 'us-tx' -> 'TX')
                            state_code = state_region.split('-')[-1].upper() if '-' in state_region else state_region.upper()
                            
                            # Keep the entry with highest confidence for each plate
                            if confidence > unique_plates[license_plate]['confidence']:
                                unique_plates[license_plate] = {
                                    'state': state_code,
                                    'confidence': confidence,
                                    'camera_id': camera_id,
                                    'timestamp': timestamp,
                                    'original_region': state_region,
                                    'image_filename': image_filename
                                }
                                
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log_event(f"Error loading plates data: {e}")
    
    # Convert to list format
    plates_list = []
    for plate, info in unique_plates.items():
        plates_list.append({
            'license_plate': plate,
            'state': info['state'],
            'confidence': info['confidence'],
            'camera_id': info['camera_id'],
            'timestamp': info['timestamp'],
            'original_region': info['original_region'],
            'image_filename': info['image_filename']
        })
    
    return plates_list

def load_existing_vin_results():
    """Load existing VIN lookup results to avoid duplicate API calls"""
    try:
        if os.path.exists(VIN_RESULTS_FILE):
            with open(VIN_RESULTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        log_event(f"Error loading existing VIN results: {e}")
    return {}

def save_vin_results(results):
    """Save VIN lookup results to file"""
    try:
        with open(VIN_RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        return True
    except Exception as e:
        log_event(f"Error saving VIN results: {e}")
        return False

def lookup_vin_for_plate(license_plate, state):
    """Perform VIN lookup for a single plate"""
    url = 'https://platetovin.com/api/convert'
    payload = {
        "state": state,
        "plate": license_plate
    }
    headers = {
        'Authorization': VIN_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route('/vin')
def vin_page():
    """Display VIN lookup page"""
    # Get unique plates
    plates = get_unique_plates_from_data()
    
    # Load existing VIN results
    existing_results = load_existing_vin_results()
    
    # Mark plates that already have VIN data
    for plate in plates:
        license_plate = plate['license_plate']
        original_state = plate['state']
        plate_key = f"{license_plate}_{original_state}"
        
        # First check with original state
        if plate_key in existing_results:
            plate['has_vin_data'] = True
            plate['vin_data'] = existing_results[plate_key]
        else:
            # Check if this plate exists with any other state (due to state overrides)
            plate['has_vin_data'] = False
            for vin_key, vin_result in existing_results.items():
                if vin_key.startswith(f"{license_plate}_"):
                    # Found this plate with a different state
                    plate['has_vin_data'] = True
                    plate['vin_data'] = vin_result
                    # Update the state to match what was actually used for VIN lookup
                    plate['state'] = vin_key.split('_', 1)[1]
                    break
    
    return render_template('vin.html', 
                          plates=plates,
                          total_plates=len(plates),
                          plates_with_vin=len([p for p in plates if p['has_vin_data']]))

@app.route('/api/vin/lookup', methods=['POST'])
def api_vin_lookup():
    """API endpoint to perform VIN lookups for selected plates"""
    try:
        data = request.get_json()
        selected_plates = data.get('plates', [])
        
        if not selected_plates:
            return jsonify({'error': 'No plates selected'}), 400
        
        # Load existing results
        existing_results = load_existing_vin_results()
        
        results = []
        new_lookups = 0
        
        for plate_info in selected_plates:
            license_plate = plate_info['license_plate']
            state = plate_info['state']
            plate_key = f"{license_plate}_{state}"
            
            # Check if we already have results for this plate
            if plate_key in existing_results:
                results.append({
                    'license_plate': license_plate,
                    'state': state,
                    'status': 'existing',
                    'data': existing_results[plate_key]
                })
                continue
            
            # Perform new lookup
            log_event(f"VIN Lookup: {license_plate} ({state})")
            vin_data = lookup_vin_for_plate(license_plate, state)
            
            # Add metadata
            result_entry = {
                'license_plate': license_plate,
                'state': state,
                'original_region': plate_info.get('original_region'),
                'confidence': plate_info.get('confidence'),
                'camera_id': plate_info.get('camera_id'),
                'timestamp': plate_info.get('timestamp'),
                'vin_lookup': vin_data,
                'lookup_timestamp': datetime.now().isoformat()
            }
            
            # Save to existing results
            existing_results[plate_key] = result_entry
            
            results.append({
                'license_plate': license_plate,
                'state': state,
                'status': 'success' if 'error' not in vin_data else 'error',
                'data': result_entry
            })
            
            new_lookups += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        # Save updated results
        if save_vin_results(existing_results):
            log_event(f"VIN Lookup completed: {new_lookups} new lookups, {len(results)} total results")
            return jsonify({
                'status': 'success',
                'results': results,
                'new_lookups': new_lookups,
                'total_results': len(results)
            })
        else:
            return jsonify({'error': 'Failed to save results'}), 500
            
    except Exception as e:
        log_event(f"Error in VIN lookup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vin/results')
def api_vin_results():
    """API endpoint to get all VIN lookup results"""
    try:
        results = load_existing_vin_results()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vin/data')
def api_get_vin_data():
    """API endpoint to get VIN data for a specific plate"""
    try:
        license_plate = request.args.get('plate')
        state = request.args.get('state')
        
        if not license_plate or not state:
            return jsonify({'error': 'Both plate and state parameters are required'}), 400
        
        # Load existing results
        existing_results = load_existing_vin_results()
        plate_key = f"{license_plate}_{state}"
        
        if plate_key in existing_results:
            return jsonify({
                'status': 'success',
                'vin_data': existing_results[plate_key]
            })
        else:
            return jsonify({
                'status': 'error',
                'error': 'No VIN data found for this plate'
            }), 404
            
    except Exception as e:
        log_event(f"Error fetching VIN data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vin/clear', methods=['POST'])
def api_clear_vin_data():
    """API endpoint to clear VIN data for selected plates"""
    try:
        data = request.get_json()
        plates_to_clear = data.get('plates', [])
        
        if not plates_to_clear:
            return jsonify({'error': 'No plates specified for clearing'}), 400
        
        # Load existing results
        existing_results = load_existing_vin_results()
        
        cleared_count = 0
        not_found_count = 0
        
        for plate_info in plates_to_clear:
            license_plate = plate_info['license_plate']
            state = plate_info['state']
            plate_key = f"{license_plate}_{state}"
            
            if plate_key in existing_results:
                del existing_results[plate_key]
                cleared_count += 1
                log_event(f"Cleared VIN data for: {license_plate} ({state})")
            else:
                not_found_count += 1
        
        # Save updated results
        if save_vin_results(existing_results):
            log_event(f"VIN data cleared: {cleared_count} plates cleared, {not_found_count} not found")
            return jsonify({
                'status': 'success',
                'cleared_count': cleared_count,
                'not_found_count': not_found_count,
                'message': f'Successfully cleared VIN data for {cleared_count} plates'
            })
        else:
            return jsonify({'error': 'Failed to save updated results'}), 500
            
    except Exception as e:
        log_event(f"Error clearing VIN data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vin/clear_all', methods=['POST'])
def api_clear_all_vin_data():
    """API endpoint to clear all VIN data"""
    try:
        # Create empty results file
        if save_vin_results({}):
            log_event("All VIN data cleared")
            return jsonify({
                'status': 'success',
                'message': 'All VIN data has been cleared'
            })
        else:
            return jsonify({'error': 'Failed to clear VIN data'}), 500
            
    except Exception as e:
        log_event(f"Error clearing all VIN data: {e}")
        return jsonify({'error': str(e)}), 500

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