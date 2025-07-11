import json
import requests

def get_VIN_from_plate(license_plate, state):
    """Get VIN information from license plate and state"""
    url = 'https://platetovin.com/api/convert'
    payload = {
        "state": state,
        "plate": license_plate
    }
    headers = {
        'Authorization': 'ehifeCWYw8awg2G',  # input API key (under account settings)
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    """Simple interactive VIN lookup test"""
    print("=== VIN Lookup Test ===")
    print("Enter a license plate and state to lookup VIN information.")
    print("Type 'quit' to exit.\n")
    
    while True:
        # Get license plate input
        license_plate = input("Enter license plate: ").strip().upper()
        if license_plate.lower() == 'quit':
            print("Goodbye!")
            break
        
        if not license_plate:
            print("Please enter a valid license plate.\n")
            continue
        
        # Get state input
        state = input("Enter state (e.g., TX, CA, NY): ").strip().upper()
        if state.lower() == 'quit':
            print("Goodbye!")
            break
        
        if not state:
            print("Please enter a valid state.\n")
            continue
        
        print(f"\nLooking up: {license_plate} ({state})")
        print("-" * 50)
        
        # Perform VIN lookup
        result = get_VIN_from_plate(license_plate, state)
        
        # Display results
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("✅ VIN Lookup Results:")
            
            if result.get('success') and 'vin' in result:
                vin_data = result['vin']
                
                # print(f"🚗 Vehicle Information:")
                print(f"   VIN:          {vin_data.get('vin', 'Unknown')}")
                print(f"   Vehicle:      {vin_data.get('name', 'Unknown')}")
                print(f"   Year:         {vin_data.get('year', 'Unknown')}")
                print(f"   Make:         {vin_data.get('make', 'Unknown')}")
                print(f"   Model:        {vin_data.get('model', 'Unknown')}")
                print(f"   Trim:         {vin_data.get('trim', 'Unknown')}")
                print(f"   Style:        {vin_data.get('style', 'Unknown')}")
                print(f"   Engine:       {vin_data.get('engine', 'Unknown')}")
                print(f"   Transmission: {vin_data.get('transmission', 'Unknown')}")
                print(f"   Drive Type:   {vin_data.get('driveType', 'Unknown')}")
                print(f"   Fuel Type:    {vin_data.get('fuel', 'Unknown')}")
                print(f"   GVWR:         {vin_data.get('GVWR', 'Unknown')}")
                
                # Handle color information
                color_info = vin_data.get('color', {})
                if isinstance(color_info, dict):
                    color_name = color_info.get('name', 'Unknown')
                    color_abbr = color_info.get('abbreviation', '')
                    color_display = f"{color_name} ({color_abbr})" if color_abbr and color_abbr != 'UNK' else color_name
                else:
                    color_display = str(color_info) if color_info else 'Unknown'
                
                print(f"   Color:        {color_display}")
                
            else:
                print("⚠️  Unexpected response format:")
                print(json.dumps(result, indent=2))
        
        print("-" * 50)
        print()

if __name__ == "__main__":
    main()