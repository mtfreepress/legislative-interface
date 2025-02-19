import requests
import json
import os

# API URL
state_api_url = "https://api.legmt.gov/legislators/v1/legislators"
# TODO: Change this in 2027
roster_url = "https://raw.githubusercontent.com/mtfreepress/capitol-tracker-2025/bcd90507bfbae87a0ac08a1132ccf74b72647396/inputs/lawmakers/legislator-roster-2025.json"

# Get the directory of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
directory_path = os.path.join(BASE_DIR, "./downloads/legislators")
os.makedirs(directory_path, exist_ok=True)

# Fetch and save legislators.json
response = requests.get(state_api_url)
if response.status_code == 200:
    file_path = os.path.join(directory_path, "legislators.json")
    with open(file_path, "w") as json_file:
        json.dump(response.json(), json_file, indent=2)
    print(f"Data saved to {file_path}")
else:
    print(f"Failed to fetch data from API. Status code: {response.status_code}")

# TODO: Change this in 2027 
# Download legislator-roster-2025.json from GitHub/Capitol Tracker
roster_response = requests.get(roster_url)
if roster_response.status_code == 200:
    roster_file_path = os.path.join(directory_path, "legislator-roster-2025.json")
    with open(roster_file_path, "w") as json_file:
        json.dump(roster_response.json(), json_file, indent=2)
    print(f"Roster data saved to {roster_file_path}")
else:
    print(f"Failed to fetch roster data. Status code: {roster_response.status_code}")