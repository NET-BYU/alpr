from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Output files
raw_output_file = 'alpr_raw_data.jsonl'
parsed_output_file = 'alpr_parsed_data.jsonl'
event_log_file = 'event.log'

def log_event(message):
    """Log events to the event log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(event_log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

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
                # Save parsed data
                with open(parsed_output_file, 'a') as f:
                    f.write(json.dumps(parsed_data) + '\n')
                
                # Log license plate event
                plate = parsed_data['license_plate']
                state = parsed_data['state_region'] or 'Unknown'
                timestamp = parsed_data['timestamp'] or 'Unknown'
                confidence = parsed_data.get('confidence', 0)
                
                log_event(f"LICENSE PLATE - {plate} ({state}) at {timestamp} - {confidence:.1f}% confidence")
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
        
        return jsonify({
            'raw_records': raw_count,
            'parsed_plates': parsed_count,
            'files': {
                'raw_data': raw_output_file,
                'parsed_data': parsed_output_file,
                'event_log': event_log_file
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize log file
    log_event("ALPR Integrated Server starting up...")
    log_event(f"Raw data will be saved to: {os.path.abspath(raw_output_file)}")
    log_event(f"Parsed data will be saved to: {os.path.abspath(parsed_output_file)}")
    log_event(f"Event log: {os.path.abspath(event_log_file)}")
    log_event(f"Configure openALPR to POST to: http://localhost:5000/alpr")
    log_event("Server ready to receive data...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)