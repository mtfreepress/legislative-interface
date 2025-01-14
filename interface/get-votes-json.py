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

# save data to file ie `HB-1-raw-votes.json`
def save_merged_data(data, bill_type, bill_number, download_dir):
    file_name = f"{bill_type}-{bill_number}-raw-votes.json"
    file_path = os.path.join(download_dir, file_name)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def main():
    args = parse_arguments()
    legislative_session = args.legislative_session
    download_dir = get_download_dir(legislative_session)

    # Ensure the download directory exists
    os.makedirs(download_dir, exist_ok=True)

    bills = load_bills(LIST_BILLS_PATH)

    for bill in bills:
        lc_number = bill['id']
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        try:
            print(f"Fetching vote data for LC{lc_number} ({bill_type} {bill_number})...")
            vote_data_url = f"https://api.legmt.gov/bills/v1/votes/findByBillId?billId={lc_number}"
            vote_data = fetch_data(vote_data_url)

            print(f"Fetching executive action data for LC{lc_number} ({bill_type} {bill_number})...")
            exec_action_url = f"https://api.legmt.gov/committees/v1/executiveActions/findByBillId?billId={lc_number}"
            exec_action_data = fetch_data(exec_action_url)

            # Merge both data into a single list
            merged_data = vote_data + exec_action_data

            # Save the merged data
            save_merged_data(merged_data, bill_type, bill_number, download_dir)
            print(f"Saved merged data for {bill_type} {bill_number}.")
        except requests.RequestException as e:
            print(f"Failed to fetch data for LC{lc_number}: {e}")

if __name__ == "__main__":
    main()
