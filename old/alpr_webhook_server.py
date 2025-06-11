from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Output file for storing ALPR results
output_file = 'alpr_results.jsonl'

@app.route('/alpr', methods=['POST'])
def receive_alpr_data():
    try:
        # Get JSON data from the POST request
        json_data = request.get_json()
        
        if json_data is None:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Add timestamp to the data
        json_data['timestamp'] = datetime.now().isoformat()
        
        # Append to file
        with open(output_file, 'a') as f:
            f.write(json.dumps(json_data) + '\n')
        
        print(f"Received ALPR data: {json_data}")
        
        # Return success response
        return jsonify({'status': 'success', 'message': 'Data received'}), 200
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    print(f"Starting ALPR webhook server...")
    print(f"Data will be saved to: {os.path.abspath(output_file)}")
    print(f"Configure openALPR to POST to: http://localhost:5000/alpr")
    app.run(host='0.0.0.0', port=5000, debug=True)