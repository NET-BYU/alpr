"""
ALPR Integrated Server
A Flask-based server for processing Automatic License Plate Recognition (ALPR) data,
providing real-time dashboard visualization and VIN lookup functionality.
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import json
import os
import base64
import yaml
import requests
import time
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

# Check if VIN functionality is enabled
VIN_ENABLED = os.environ.get('ENABLE_VIN', 'false').lower() == 'true'

# Configuration Loading
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)['integrated_server']

# File paths from configuration
RAW_OUTPUT_FILE = config.get('raw_output_file', 'alpr_raw_data.jsonl')
PARSED_OUTPUT_FILE = config.get('parsed_output_file', 'alpr_parsed_data.jsonl')
EVENT_LOG_FILE = config.get('event_log_file', 'event.log')
PLATES_DIR = config.get('plates_dir', 'plates')
VIN_RESULTS_FILE = config.get('vin_results_file', 'alpr_vin_lookup.json')

# API Configuration (only if VIN is enabled)
if VIN_ENABLED:
    VIN_API_KEY = 'ehifeCWYw8awg2G'  # TODO: Move to config.yaml for production

# Initialize directories
if not os.path.exists(PLATES_DIR):
    os.makedirs(PLATES_DIR)

# =====================================================================================
# UTILITY FUNCTIONS
# =====================================================================================

def log_event(message):
    """Log events to the event log file with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(EVENT_LOG_FILE, 'a') as f:
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
        
        # Create safe filename components
        safe_plate = "".join(c for c in plate_number if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_region = region.replace('-', '_')
        
        # Parse timestamp for filename
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y%m%d_%H%M%S')
        except:
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"{safe_plate}_{safe_region}_{time_str}_{confidence:.1f}.jpg"
        filepath = os.path.join(PLATES_DIR, filename)
        
        # Decode base64 and save JPEG
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
        vehicle = data.get('vehicle', {})
        return {
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
                'color': vehicle.get('color', [{}])[0].get('name') if vehicle.get('color') else None,
                'color_confidence': vehicle.get('color', [{}])[0].get('confidence') if vehicle.get('color') else None,
                'make': vehicle.get('make', [{}])[0].get('name') if vehicle.get('make') else None,
                'make_confidence': vehicle.get('make', [{}])[0].get('confidence') if vehicle.get('make') else None,
                'body_type': vehicle.get('body_type', [{}])[0].get('name') if vehicle.get('body_type') else None,
                'year_range': vehicle.get('year', [{}])[0].get('name') if vehicle.get('year') else None
            },
            'uuid': data.get('best_uuid')
        }
    except Exception as e:
        log_event(f"Error parsing license plate data: {e}")
        return None

# =====================================================================================
# API ROUTES - ALPR Data Processing
# =====================================================================================

@app.route('/alpr', methods=['POST'])
def receive_alpr_data():
    """Receive and process ALPR data from openALPR"""
    try:
        json_data = request.get_json()
        if json_data is None:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Add timestamp if not present
        if 'timestamp' not in json_data:
            json_data['timestamp'] = datetime.now().isoformat()
        
        # Save raw data
        with open(RAW_OUTPUT_FILE, 'a') as f:
            f.write(json.dumps(json_data) + '\n')
        
        # Process based on data type
        data_type = json_data.get('data_type', 'unknown')
        
        if data_type == 'heartbeat':
            # Process heartbeat data
            video_streams = json_data.get('video_streams', [])
            total_plate_reads = sum(stream.get('total_plate_reads', 0) for stream in video_streams)
            
            # Find most recent plate read timestamp
            last_plate_read = max((stream.get('last_plate_read', 0) for stream in video_streams), default=0)
            last_plate_time = "Never"
            if last_plate_read > 0:
                try:
                    last_plate_time = datetime.fromtimestamp(last_plate_read / 1000).strftime('%H:%M:%S')
                except:
                    last_plate_time = "Unknown"
            
            log_event(f"heartbeat - Total plates: {total_plate_reads}, Last read: {last_plate_time}")
            
        elif data_type == 'alpr_group':
            # Process license plate data
            parsed_data = parse_license_plate_data(json_data)
            
            if parsed_data and parsed_data.get('license_plate'):
                # Save plate image
                image_filename = save_plate_image(json_data)
                if image_filename:
                    parsed_data['image_filename'] = image_filename
                
                # Save parsed data
                with open(PARSED_OUTPUT_FILE, 'a') as f:
                    f.write(json.dumps(parsed_data) + '\n')
                
                # Log plate detection
                plate = parsed_data['license_plate']
                state = parsed_data['state_region'] or 'Unknown'
                confidence = parsed_data.get('confidence', 0)
                image_msg = f" (Image: {image_filename})" if image_filename else ""
                
                log_event(f"LICENSE PLATE - {plate} ({state}) - {confidence:.1f}% confidence{image_msg}")
            else:
                log_event("alpr_group received but no valid license plate data found")
        else:
            log_event(f"Received data type: {data_type}")
        
        return jsonify({'status': 'success', 'message': 'Data received and processed'}), 200
        
    except Exception as e:
        log_event(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================================================
# WEB ROUTES - Dashboard and UI
# =====================================================================================

@app.route('/dashboard')
def dashboard():
    """Display ALPR dashboard"""
    return render_template('dashboard.html', vin_enabled=VIN_ENABLED)

@app.route('/api/plates')
def get_plates():
    """API endpoint to get all plate data"""
    plates = []
    try:
        if os.path.exists(PARSED_OUTPUT_FILE):
            with open(PARSED_OUTPUT_FILE, 'r') as f:
                for line in f:
                    try:
                        plates.append(json.loads(line.strip()))
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
        if os.path.exists(EVENT_LOG_FILE):
            with open(EVENT_LOG_FILE, 'r') as f:
                lines = f.readlines()
                # Get last 10 events
                recent_lines = lines[-10:] if len(lines) > 10 else lines
                events = [line.strip() for line in recent_lines if line.strip()]
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify(events)

@app.route('/plates/<filename>')
def serve_plate_image(filename):
    """Serve plate images"""
    return send_from_directory(PLATES_DIR, filename)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'vin_enabled': VIN_ENABLED}), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get basic statistics about processed data"""
    try:
        # Count records in files
        raw_count = 0
        parsed_count = 0
        image_count = 0
        
        if os.path.exists(RAW_OUTPUT_FILE):
            with open(RAW_OUTPUT_FILE, 'r') as f:
                raw_count = sum(1 for line in f)
        
        if os.path.exists(PARSED_OUTPUT_FILE):
            with open(PARSED_OUTPUT_FILE, 'r') as f:
                parsed_count = sum(1 for line in f)
        
        if os.path.exists(PLATES_DIR):
            image_count = len([f for f in os.listdir(PLATES_DIR) if f.endswith('.jpg')])
        
        return jsonify({
            'raw_records': raw_count,
            'parsed_plates': parsed_count,
            'plate_images': image_count,
            'vin_enabled': VIN_ENABLED,
            'files': {
                'raw_data': RAW_OUTPUT_FILE,
                'parsed_data': PARSED_OUTPUT_FILE,
                'event_log': EVENT_LOG_FILE,
                'plates_directory': PLATES_DIR
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================================================
# VIN LOOKUP FUNCTIONALITY (Only if enabled)
# =====================================================================================

if VIN_ENABLED:
    def load_existing_vin_results():
        """Load existing VIN lookup results"""
        try:
            if os.path.exists(VIN_RESULTS_FILE):
                with open(VIN_RESULTS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            log_event(f"Error loading VIN results: {e}")
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
        payload = {"state": state, "plate": license_plate}
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

    def get_unique_plates_from_data():
        """Get unique license plates from parsed ALPR data"""
        unique_plates = defaultdict(lambda: {
            'state': None, 'confidence': 0, 'camera_id': None, 
            'timestamp': None, 'image_filename': None
        })
        
        try:
            if os.path.exists(PARSED_OUTPUT_FILE):
                with open(PARSED_OUTPUT_FILE, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            license_plate = data.get('license_plate')
                            state_region = data.get('state_region')
                            confidence = data.get('confidence', 0)
                            
                            if license_plate and state_region:
                                # Extract state code from region
                                state_code = state_region.split('-')[-1].upper() if '-' in state_region else state_region.upper()
                                
                                # Keep entry with highest confidence for each plate
                                if confidence > unique_plates[license_plate]['confidence']:
                                    unique_plates[license_plate] = {
                                        'state': state_code,
                                        'confidence': confidence,
                                        'camera_id': data.get('camera_id'),
                                        'timestamp': data.get('timestamp'),
                                        'original_region': state_region,
                                        'image_filename': data.get('image_filename')
                                    }
                                    
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            log_event(f"Error loading plates data: {e}")
        
        # Convert to list format
        return [{
            'license_plate': plate,
            'state': info['state'],
            'confidence': info['confidence'],
            'camera_id': info['camera_id'],
            'timestamp': info['timestamp'],
            'original_region': info['original_region'],
            'image_filename': info['image_filename']
        } for plate, info in unique_plates.items()]

    # =====================================================================================
    # VIN LOOKUP API ROUTES (Only if enabled)
    # =====================================================================================

    @app.route('/vin')
    def vin_page():
        """Display VIN lookup page"""
        plates = get_unique_plates_from_data()
        existing_results = load_existing_vin_results()
        
        # Mark plates that already have VIN data
        for plate in plates:
            license_plate = plate['license_plate']
            original_state = plate['state']
            plate_key = f"{license_plate}_{original_state}"
            
            # Check if VIN data exists
            if plate_key in existing_results:
                plate['has_vin_data'] = True
                plate['vin_data'] = existing_results[plate_key]
            else:
                # Check if plate exists with different state
                plate['has_vin_data'] = False
                for vin_key, vin_result in existing_results.items():
                    if vin_key.startswith(f"{license_plate}_"):
                        plate['has_vin_data'] = True
                        plate['vin_data'] = vin_result
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
            
            existing_results = load_existing_vin_results()
            results = []
            new_lookups = 0
            
            for plate_info in selected_plates:
                license_plate = plate_info['license_plate']
                state = plate_info['state']
                plate_key = f"{license_plate}_{state}"
                
                # Check existing results
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
                
                # Create result entry
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
                
                existing_results[plate_key] = result_entry
                results.append({
                    'license_plate': license_plate,
                    'state': state,
                    'status': 'success' if 'error' not in vin_data else 'error',
                    'data': result_entry
                })
                
                new_lookups += 1
                time.sleep(0.5)  # Rate limiting
            
            # Save results
            if save_vin_results(existing_results):
                log_event(f"VIN Lookup completed: {new_lookups} new, {len(results)} total")
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
            return jsonify(load_existing_vin_results())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/vin/data')
    def api_get_vin_data():
        """API endpoint to get VIN data for a specific plate"""
        try:
            license_plate = request.args.get('plate')
            state = request.args.get('state')
            
            if not license_plate or not state:
                return jsonify({'error': 'Both plate and state parameters required'}), 400
            
            existing_results = load_existing_vin_results()
            plate_key = f"{license_plate}_{state}"
            
            if plate_key in existing_results:
                return jsonify({'status': 'success', 'vin_data': existing_results[plate_key]})
            else:
                return jsonify({'status': 'error', 'error': 'No VIN data found'}), 404
                
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
                return jsonify({'error': 'No plates specified'}), 400
            
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
                    log_event(f"Cleared VIN data: {license_plate} ({state})")
                else:
                    not_found_count += 1
            
            if save_vin_results(existing_results):
                log_event(f"VIN data cleared: {cleared_count} plates")
                return jsonify({
                    'status': 'success',
                    'cleared_count': cleared_count,
                    'not_found_count': not_found_count,
                    'message': f'Cleared VIN data for {cleared_count} plates'
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
            if save_vin_results({}):
                log_event("All VIN data cleared")
                return jsonify({'status': 'success', 'message': 'All VIN data cleared'})
            else:
                return jsonify({'error': 'Failed to clear VIN data'}), 500
                
        except Exception as e:
            log_event(f"Error clearing all VIN data: {e}")
            return jsonify({'error': str(e)}), 500

else:
    # If VIN is disabled, return 404 for VIN routes
    @app.route('/vin')
    def vin_disabled():
        return jsonify({'error': 'VIN functionality is disabled'}), 404
    
    @app.route('/api/vin/<path:subpath>', methods=['GET', 'POST'])
    def api_vin_disabled(subpath):
        return jsonify({'error': 'VIN functionality is disabled'}), 404

# =====================================================================================
# APPLICATION STARTUP
# =====================================================================================

if __name__ == '__main__':
    # Initialize application
    log_event("ALPR Integrated Server starting up...")
    log_event(f"VIN functionality: {'ENABLED' if VIN_ENABLED else 'DISABLED'}")
    log_event(f"Raw data: {os.path.abspath(RAW_OUTPUT_FILE)}")
    log_event(f"Parsed data: {os.path.abspath(PARSED_OUTPUT_FILE)}")
    log_event(f"Event log: {os.path.abspath(EVENT_LOG_FILE)}")
    log_event(f"Plate images: {os.path.abspath(PLATES_DIR)}")
    log_event("Configure openALPR to POST to: http://localhost:5000/alpr")
    log_event("Server ready to receive data...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)