import os
import json
import requests
import glob
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
LOOKUP_DIR = os.path.join(BASE_DIR, "requester-lookup")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Fetch and save agency data for bill requesters")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    return parser.parse_args()

def load_bill_data(session_id):
    """Load bill data from raw-{session_id}-bills files using the standard naming pattern"""
    agency_ids = set()
    by_request_of_ids = set()
    
    bills_dir = os.path.join(DOWNLOAD_DIR, f"raw-{session_id}-bills")
    bill_pattern = os.path.join(bills_dir, "*-*-raw-bill.json")
    
    if os.path.exists(bills_dir):
        bill_files = glob.glob(bill_pattern)
        # print(f"Found {len(bill_files)} bill files in {bills_dir}")   
        
        for bill_file in bill_files:
            try:
                with open(bill_file, 'r') as f:
                    bill = json.load(f)
                    if bill.get("draft"):
                        if bill["draft"].get("requesterType") == "AGENCY":
                            agency_ids.add(bill["draft"]["requesterId"])
                        if "byRequestOfs" in bill["draft"]:
                            for by_request_of in bill["draft"]["byRequestOfs"]:
                                by_request_of_ids.add(by_request_of["byRequestOfId"])
            except json.JSONDecodeError:
                print(f"Error parsing JSON in {bill_file}")
    else:
        # fallback to consolidated JSON file — should never happen but just in case
        raw_bills_file = os.path.join(BASE_DIR, "..", f"raw-{session_id}-bills.json")
        if os.path.exists(raw_bills_file):
            # print(f"Bills directory not found. Loading from consolidated file: {raw_bills_file}")
            with open(raw_bills_file, 'r') as f:
                bills = json.load(f)
                for bill in bills:
                    if bill.get("draft"):
                        if bill["draft"].get("requesterType") == "AGENCY":
                            agency_ids.add(bill["draft"]["requesterId"])
                        if "byRequestOfs" in bill["draft"]:
                            for by_request_of in bill["draft"]["byRequestOfs"]:
                                by_request_of_ids.add(by_request_of["byRequestOfId"])
        else:
            print(f"No bill files found in expected locations for session {session_id}")
    
    return list(agency_ids), list(by_request_of_ids)

def fetch_agency(agency_id):
    """Fetch agency details from API"""
    url = f"https://api.legmt.gov/legislators/v1/organizations/{agency_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            agency_data = response.json()
            return {
                "id": agency_id,
                "agency": agency_data.get("name", "Unknown Agency")
            }
        else:
            # print(f"Failed to fetch agency {agency_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching agency {agency_id}: {e}")
        return None

def main():
    args = parse_args()
    session_id = args.sessionId
    
    # create directory if it doesn't exist
    os.makedirs(LOOKUP_DIR, exist_ok=True)
    
    # set output file with session ID
    agencies_lookup_file = os.path.join(LOOKUP_DIR, f"agencies-lookup.json")
    
    # get existing agency lookup data if it exists
    existing_agency_lookup = {}
    if os.path.exists(agencies_lookup_file):
        try:
            with open(agencies_lookup_file, 'r') as f:
                existing_agency_lookup = json.load(f)
            # print(f"Loaded {len(existing_agency_lookup)} existing agencies from {agencies_lookup_file}")
        except json.JSONDecodeError:
            print(f"Error parsing existing agency file: {agencies_lookup_file}")
    
    # get agency IDs and byRequestOf IDs from bill data
    agency_ids, by_request_of_ids = load_bill_data(session_id)
    # print(f"Found {len(agency_ids)} agency IDs and {len(by_request_of_ids)} byRequestOf IDs in bills for session {session_id}")
    
    # combine both sets of IDs
    all_ids = set(agency_ids + by_request_of_ids)
    
    # filter IDs that are already in our lookup
    new_ids = [id for id in all_ids if str(id) not in existing_agency_lookup]
    # print(f"Of which {len(new_ids)} are new agencies to fetch")
    
    # get details for new agencies
    new_agencies = {}
    if new_ids:
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {executor.submit(fetch_agency, agency_id): agency_id for agency_id in new_ids}
            for future in as_completed(future_to_id):
                agency_id = future_to_id[future]
                try:
                    agency = future.result()
                    if agency:  # Only add if we successfully fetched the agency
                        new_agencies[str(agency_id)] = agency
                        # print(f"Added new agency: {agency['agency']}")
                except Exception as e:
                    print(f"Error processing agency {agency_id}: {e}")
    
    # merge existing and new agencies
    merged_agency_lookup = {**existing_agency_lookup, **{str(k): v for k, v in new_agencies.items()}}
    
    # save if we have changes
    if len(merged_agency_lookup) > len(existing_agency_lookup):
        with open(agencies_lookup_file, 'w') as f:
            json.dump(merged_agency_lookup, f, indent=2)
        # print(f"Updated agency lookup saved to {agencies_lookup_file} with {len(merged_agency_lookup)} agencies")
    else:
        print(f"No new agencies found. Keeping existing file with {len(existing_agency_lookup)} agencies.")

if __name__ == "__main__":
    main()