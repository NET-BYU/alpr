import json
import base64
from datetime import datetime
import os

def extract_plate_images(input_file='alpr_raw_data.jsonl', output_dir='plates'):
    """Extract plate crop JPEG images from ALPR raw data"""
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    extracted_count = 0
    skipped_count = 0
    
    with open(input_file, 'r') as infile:
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line.strip())
                
                # Skip if not an alpr_group (skip heartbeat, etc.)
                if data.get('data_type') != 'alpr_group':
                    skipped_count += 1
                    continue
                
                # Check if best_plate and plate_crop_jpeg exist
                best_plate = data.get('best_plate', {})
                plate_crop_jpeg = best_plate.get('plate_crop_jpeg')
                
                if not plate_crop_jpeg:
                    skipped_count += 1
                    continue
                
                # Extract plate info for filename
                plate_number = best_plate.get('plate', 'UNKNOWN')
                confidence = best_plate.get('confidence', 0)
                region = best_plate.get('region', 'unknown')
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                # Create a safe filename
                # Remove invalid filename characters
                safe_plate = "".join(c for c in plate_number if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_region = region.replace('-', '_')
                
                # Parse timestamp for filename
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y%m%d_%H%M%S')
                except:
                    time_str = f"line_{line_num}"
                
                filename = f"{safe_plate}_{safe_region}_{time_str}_{confidence:.1f}.jpg"
                filepath = os.path.join(output_dir, filename)
                
                # Decode base64 and save as JPEG
                try:
                    # The plate_crop_jpeg field contains base64-encoded JPEG data
                    jpeg_data = base64.b64decode(plate_crop_jpeg)
                    
                    with open(filepath, 'wb') as img_file:
                        img_file.write(jpeg_data)
                    
                    print(f"Extracted: {filename} (Confidence: {confidence:.1f}%)")
                    extracted_count += 1
                    
                except Exception as decode_error:
                    print(f"Error decoding image for line {line_num}: {decode_error}")
                    skipped_count += 1
                    
            except json.JSONDecodeError:
                print(f"Error parsing JSON on line {line_num}")
                skipped_count += 1
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                skipped_count += 1
    
    print(f"\nSummary:")
    print(f"Images extracted: {extracted_count}")
    print(f"Lines skipped: {skipped_count}")
    print(f"Images saved to: {os.path.abspath(output_dir)}")

def extract_single_plate(license_plate, input_file='alpr_raw_data.jsonl', output_dir='plates'):
    """Extract images for a specific license plate"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    found_count = 0
    
    with open(input_file, 'r') as infile:
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line.strip())
                
                if data.get('data_type') != 'alpr_group':
                    continue
                
                best_plate = data.get('best_plate', {})
                plate_number = best_plate.get('plate', '')
                
                # Check if this is the plate we're looking for
                if plate_number.upper() != license_plate.upper():
                    continue
                
                plate_crop_jpeg = best_plate.get('plate_crop_jpeg')
                if not plate_crop_jpeg:
                    continue
                
                # Extract and save the image
                confidence = best_plate.get('confidence', 0)
                region = best_plate.get('region', 'unknown')
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                safe_region = region.replace('-', '_')
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y%m%d_%H%M%S')
                except:
                    time_str = f"line_{line_num}"
                
                filename = f"{license_plate}_{safe_region}_{time_str}_{confidence:.1f}.jpg"
                filepath = os.path.join(output_dir, filename)
                
                jpeg_data = base64.b64decode(plate_crop_jpeg)
                with open(filepath, 'wb') as img_file:
                    img_file.write(jpeg_data)
                
                print(f"Found and extracted: {filename}")
                found_count += 1
                
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
    
    if found_count == 0:
        print(f"No images found for license plate: {license_plate}")
    else:
        print(f"Extracted {found_count} images for {license_plate}")

if __name__ == "__main__":
    import sys
    
    # FILE FORMAT:
    #
    # {LICENSE_PLATE}_{REGION}_{TIMESTAMP}_{CONFIDENCE}.jpg

    if len(sys.argv) > 1:
        # Extract images for a specific license plate
        license_plate = sys.argv[1]
        print(f"Extracting images for license plate: {license_plate}")
        extract_single_plate(license_plate)
    else:
        # Extract all images
        print("Extracting all license plate images...")
        extract_plate_images()