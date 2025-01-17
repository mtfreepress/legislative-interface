import json
import os
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_BILLS_PATH = os.path.join(BASE_DIR, '../list-bills-2.json')

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch and save executive actions data for bills.")
    parser.add_argument('legislative_session', type=str, help="Legislative session identifier")
    return parser.parse_args()

def get_download_dir(legislative_session):
    path = os.path.join(BASE_DIR, f'downloads/raw-{legislative_session}-executive-actions')
    os.makedirs(path, exist_ok=True) 
    return path

def load_bills(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def save_executive_actions_data(data, bill_type, bill_number, download_dir):
    file_name = f"{bill_type}-{bill_number}-executive-actions.json"
    file_path = os.path.join(download_dir, file_name)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def fetch_and_save_executive_actions_data(bill, download_dir):
    lc_number = bill['id']
    bill_type = bill['billType']
    bill_number = bill['billNumber']
    try:
        executive_actions_url = f"https://api.legmt.gov/committees/v1/executiveActions/findByBillId?billId={lc_number}"
        executive_actions_data = fetch_data(executive_actions_url)
        save_executive_actions_data(executive_actions_data, bill_type, bill_number, download_dir)
    except requests.RequestException as e:
        print(f"Failed to fetch data for LC{lc_number}: {e}")

def main():
    args = parse_arguments()
    legislative_session = args.legislative_session
    download_dir = get_download_dir(legislative_session)
    bills = load_bills(LIST_BILLS_PATH)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_and_save_executive_actions_data, bill, download_dir) for bill in bills]
        for future in as_completed(futures):
            future.result()  # To raise exceptions if any

if __name__ == "__main__":
    main()


# Singlthread - takes about 70 seconds
# import json
# import os
# import requests
# import argparse

# # relative to file - not where it is called
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# LIST_BILLS_PATH = os.path.join(BASE_DIR, '../list-bills-2.json')

# # takes legislative session as arg
# def parse_arguments():
#     parser = argparse.ArgumentParser(description="Fetch and save executive actions data for bills.")
#     parser.add_argument('legislative_session', type=str, help="Legislative session identifier")
#     return parser.parse_args()

# # get download directory, create if doesn't exist rather than throwing an error
# def get_download_dir(legislative_session):
#     path = os.path.join(BASE_DIR, f'downloads/raw-{legislative_session}-executive-actions')
#     os.makedirs(path, exist_ok=True) 
#     return path

# # load bill list
# def load_bills(file_path):
#     with open(file_path, 'r') as file:
#         return json.load(file)

# # fetch executive actions data jsons
# def fetch_data(url):
#     # print(f"DEBUG: Fetching URL: {url}")
#     response = requests.get(url)
#     response.raise_for_status()
#     return response.json()

# # save data to file ie `HB-1-executive-actions.json`
# def save_executive_actions_data(data, bill_type, bill_number, download_dir):
#     file_name = f"{bill_type}-{bill_number}-executive-actions.json"
#     file_path = os.path.join(download_dir, file_name)
#     with open(file_path, 'w') as file:
#         json.dump(data, file, indent=4)

# def main():
#     args = parse_arguments()
#     legislative_session = args.legislative_session
#     download_dir = get_download_dir(legislative_session)

#     # Ensure the download directory exists
#     os.makedirs(download_dir, exist_ok=True)

#     bills = load_bills(LIST_BILLS_PATH)

#     for bill in bills:
#         lc_number = bill['id']
#         bill_type = bill['billType']
#         bill_number = bill['billNumber']

#         try:
#             # print(f"Fetching executive actions data for LC{lc_number} ({bill_type} {bill_number})...")
#             executive_actions_url = f"https://api.legmt.gov/committees/v1/executiveActions/findByBillId?billId={lc_number}"
#             executive_actions_data = fetch_data(executive_actions_url)

#             # Save the executive actions data
#             save_executive_actions_data(executive_actions_data, bill_type, bill_number, download_dir)
#             # print(f"Saved executive actions data for {bill_type} {bill_number}.")
#         except requests.RequestException as e:
#             print(f"Failed to fetch data for LC{lc_number}: {e}")

# if __name__ == "__main__":
#     main()