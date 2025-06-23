import pandas as pd

peralta2017 = pd.read_excel("Peralta2017.EPA.Matched.xlsx") ##This input changes based on what excel sheet you want to run

import requests
import json

def get_VIN_from_plate(row):
    url = 'https://platetovin.com/api/convert'
    payload = {
    "state": row['STATE'],
    "plate": row['LICENSE']
    }
    headers = {
    'Authorization': 'ehifeCWYw8awg2G', #input API key (under account settings)
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }

    try:
        response = requests.request('POST', url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

for index, row in peralta2017.iterrows():
    vehicle_data = get_VIN_from_plate(row)
    print(f"Data for row {index}: {vehicle_data}")