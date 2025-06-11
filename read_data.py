import json
from datetime import datetime

def parse_alpr_results(input_file='alpr_results.jsonl', output_file='parsed_plates.jsonl'):
    """Parse ALPR results and extract useful license plate information"""
    
    parsed_count = 0
    skipped_count = 0
    
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line.strip())
                
                # Skip if not an alpr_group (skip heartbeat, etc.)
                if data.get('data_type') != 'alpr_group':
                    skipped_count += 1
                    continue
                
                # Skip if no best_plate data
                if not data.get('best_plate'):
                    skipped_count += 1
                    continue
                
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
                
                # Only write if we have a license plate
                if parsed_data['license_plate']:
                    outfile.write(json.dumps(parsed_data) + '\n')
                    parsed_count += 1
                    print(f"Parsed: {parsed_data['license_plate']} ({parsed_data['state_region']}) - {parsed_data['confidence']:.1f}% confidence")
                else:
                    skipped_count += 1
                    
            except json.JSONDecodeError:
                print(f"Error parsing line {line_num}: Invalid JSON")
                skipped_count += 1
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                skipped_count += 1
    
    print(f"\nSummary:")
    print(f"Parsed plates: {parsed_count}")
    print(f"Skipped lines: {skipped_count}")
    print(f"Output saved to: {output_file}")

def display_parsed_data(input_file='alpr_parsed_data.jsonl'):
    """Display parsed data in a readable format"""
    
    print("\n=== PARSED ALPR DATA ===")
    with open(input_file, 'r') as infile:
        for line in infile:
            data = json.loads(line.strip())
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')) if data['timestamp'] else 'Unknown'
            
            print(f"\nLicense Plate: {data['license_plate']}")
            print(f"State/Region: {data['state_region']} ({data['region_confidence']}% confidence)")
            print(f"Plate Confidence: {data['confidence']:.1f}%")
            print(f"Timestamp: {timestamp}")
            print(f"Camera ID: {data['camera_id']}")
            
            if data['vehicle_info']['color']:
                print(f"Vehicle: {data['vehicle_info']['color']} {data['vehicle_info']['make']} {data['vehicle_info']['body_type']}")
            
            if data['travel_direction']:
                print(f"Travel Direction: {data['travel_direction']:.1f}°")
            
            print("-" * 50)

if __name__ == "__main__":
    # Parse the ALPR results
    # parse_alpr_results()
    
    # Display the parsed data
    display_parsed_data()