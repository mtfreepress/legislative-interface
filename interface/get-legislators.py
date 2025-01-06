import requests
import json
import os

# API URL
api_url = "https://api.legmt.gov/legislators/v1/legislators"

response = requests.get(api_url)

if response.status_code == 200:
    directory_path = os.path.abspath(os.path.join(os.getcwd(), "./inputs/legislators"))
    os.makedirs(directory_path, exist_ok=True)
    file_path = os.path.join(directory_path, "legislators.json")
    with open(file_path, "w") as json_file:
        json.dump(response.json(), json_file, indent=2)

    print(f"Data saved to {file_path}")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
