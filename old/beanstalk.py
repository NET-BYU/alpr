import greenstalk
import json

# Connect to beanstalkd server on localhost, default port 11300
client = greenstalk.Client(('127.0.0.1', 11300))
client.watch('alprd')  # Use the 'alprd' tube

output_file = 'alpr_results.jsonl'  # Each line is a JSON object

print("Listening for jobs... (Press Ctrl+C to stop)")

try:
    while True:
        job = client.reserve()  # Wait for a job
        data = job.body.decode('utf-8')
        # Optionally, validate JSON
        try:
            json_obj = json.loads(data)
        except json.JSONDecodeError:
            print("Received invalid JSON, skipping.")
            client.delete(job)
            continue

        # Append JSON to file
        with open(output_file, 'a') as f:
            f.write(json.dumps(json_obj) + '\n')

        print("Saved:", json_obj)
        client.delete(job)  # Remove job from queue

except KeyboardInterrupt:
    print("\nStopped.")

client.close()