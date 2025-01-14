import json
import os
import requests

# Define the base path relative to the script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_BILLS_PATH = os.path.join(BASE_DIR, '../list-bills-2.json')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads/raw-votes')

# Ensure the download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Load the list of bills from the JSON file
def load_bills(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Fetch data from the API for a given LC number
def fetch_vote_data(lc_number):
    url = f"https://api.legmt.gov/bills/v1/votes/findByBillId?billId={lc_number}"
    print(f"DEBUG: Fetching URL: {url}")  # Debugging output for URL
    response = requests.get(url)
    print(response)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()

# Save the fetched data to a file
def save_vote_data(data, bill_type, bill_number):
    file_name = f"{bill_type}-{bill_number}-raw-votes.json"
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Main script logic
def main():
    bills = load_bills(LIST_BILLS_PATH)

    for bill in bills:
        id = bill['id']
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        # lc_number = "1372"  # Hardcoded LC number for debugging
        # bill_type = "HB"
        # bill_number = 1

        try:
            print(f"Fetching data for LC{id} ({bill_type} {bill_number})...")
            vote_data = fetch_vote_data(id)
            save_vote_data(vote_data, bill_type, bill_number)
            print(f"Saved data for {bill_type} {bill_number}.")
        except requests.RequestException as e:
            print(f"Failed to fetch data for LC{id}: {e}")

if __name__ == "__main__":
    main()
