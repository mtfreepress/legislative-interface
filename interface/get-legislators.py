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
# Add new directory for lookup files
LOOKUP_DIR = os.path.join(BASE_DIR, "requester-lookup")

# Create both directories
os.makedirs(directory_path, exist_ok=True)
os.makedirs(LOOKUP_DIR, exist_ok=True)

# Fetch and save legislators.json
response = requests.get(state_api_url)
if response.status_code == 200:
    legislators_data = response.json()
    
    # Save full legislators data (keep in original location)
    file_path = os.path.join(directory_path, "legislators.json")
    with open(file_path, "w") as json_file:
        json.dump(legislators_data, json_file, indent=2)
    print(f"Data saved to {file_path}")
    
    # Create and save lookup file to new location
    lookup_data = {}
    for legislator in legislators_data:
        legislator_id = legislator.get("id")
        first_name = legislator.get("firstName", "")
        last_name = legislator.get("lastName", "")
        
        if legislator_id:
            lookup_data[legislator_id] = {
                "id": legislator_id,
                "legislatorName": f"{first_name} {last_name}".strip()
            }
    
    lookup_path = os.path.join(LOOKUP_DIR, "legislators-lookup.json")
    with open(lookup_path, "w") as lookup_file:
        json.dump(lookup_data, lookup_file, indent=2)
    print(f"Lookup data saved to {lookup_path}")
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