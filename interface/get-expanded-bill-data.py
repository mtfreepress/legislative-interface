import json
import requests
import os

# Load the JSON file with the bill data
input_file = "list-bills-2.json"
with open(input_file, "r") as file:
    bills = json.load(file)

# Define the base URL and session ID
base_url = "https://api.legmt.gov/bills/v1/bills/findBySessionIdAndDraftNumber"
session_id = 2

# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "expanded-bill-data")
os.makedirs(output_dir, exist_ok=True)

# Loop through each bill in the input JSON
for bill in bills:
    lc = bill.get("lc")
    bill_type = bill.get("billType")
    bill_number = bill.get("billNumber")

    if not lc or not bill_type or not bill_number:
        print(f"Skipping invalid bill entry: {bill}")
        continue

    # Construct the URL for the API request
    url = f"{base_url}?sessionId={session_id}&draftNumber={lc}"

    try:
        # Make the GET request to the API
        response = requests.get(url)
        response.raise_for_status()
        
        # Save the response JSON to a file
        output_filename = f"{bill_type}{bill_number}-bill-data.json"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, "w") as output_file:
            json.dump(response.json(), output_file, indent=4)
        
        print(f"Saved data for {bill_type}{bill_number} to {output_path}")

    except requests.RequestException as e:
        print(f"Error fetching data for {bill_type}{bill_number}: {e}")
