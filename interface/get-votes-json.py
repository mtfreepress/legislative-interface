import json
import os
import requests
import argparse

# relative to file - not where it is called
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_BILLS_PATH = os.path.join(BASE_DIR, '../list-bills-2.json')

# takes legislative session as arg
def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch and save vote data for bills.")
    parser.add_argument('legislative_session', type=str, help="Legislative session identifier")
    return parser.parse_args()

# get download directory, create if doesn't exist rather than throwing an error
def get_download_dir(legislative_session):
    path = os.path.join(BASE_DIR, f'downloads/raw-{legislative_session}-votes')
    os.makedirs(path, exist_ok=True) 
    return path

# load bill list
def load_bills(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# fetch vote data jsons
def fetch_data(url):
    print(f"DEBUG: Fetching URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# save data to file
def save_data(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def extract_unique_committee_ids(bills):
    """Extract unique standingCommitteeId values from bill statuses."""
    committee_ids = set()
    for bill in bills:
        draft = bill.get('draft', {})
        bill_statuses = draft.get('billStatuses', [])
        for status in bill_statuses:
            committee_id = status.get('standingCommitteeId')
            if committee_id is not None:
                committee_ids.add(committee_id)
    return sorted(committee_ids)

def main():
    args = parse_arguments()
    legislative_session = args.legislative_session
    download_dir = get_download_dir(legislative_session)

    # Ensure the download directory exists
    os.makedirs(download_dir, exist_ok=True)

    bills = load_bills(LIST_BILLS_PATH)
    unique_committee_ids = set()

    for bill in bills:
        lc_number = bill['id']
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        try:
            print(f"Fetching data for LC{lc_number} ({bill_type} {bill_number})...")
            bill_data_url = f"https://api.legmt.gov/bills/v1/findById?billId={lc_number}"
            bill_data = fetch_data(bill_data_url)

            # Extract unique committee IDs
            committee_ids = extract_unique_committee_ids([bill_data])
            unique_committee_ids.update(committee_ids)

        except requests.RequestException as e:
            print(f"Failed to fetch data for LC{lc_number}: {e}")

    # Save unique committee IDs to a file
    unique_committee_ids_path = os.path.join(download_dir, 'committee_ids.json')
    save_data(list(unique_committee_ids), unique_committee_ids_path)
    print(f"Saved unique committee IDs to {unique_committee_ids_path}")

if __name__ == "__main__":
    main()