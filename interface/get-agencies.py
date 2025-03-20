import os
import json
import requests
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
BILLS_DIR = os.path.join(BASE_DIR, "raw-2-bills")
AGENCIES_LOOKUP_FILE = os.path.join(DOWNLOAD_DIR, "agencies-lookup.json")

def load_bill_data():
    """Load bill data either from raw-2-bills.json or individual bill files"""
    agency_ids = set()
    
    # First check if we have a consolidated JSON
    raw_bills_file = os.path.join(BASE_DIR, "raw-2-bills.json")
    if os.path.exists(raw_bills_file):
        print(f"Loading bills from {raw_bills_file}")
        with open(raw_bills_file, 'r') as f:
            bills = json.load(f)
            for bill in bills:
                if bill.get("draft") and bill["draft"].get("requesterType") == "AGENCY":
                    agency_ids.add(bill["draft"]["requesterId"])
    else:
        # Load from individual bill files
        print(f"Loading bills from individual files in {BILLS_DIR}")
        bill_files = glob.glob(os.path.join(BILLS_DIR, "*", "*.json"))
        for bill_file in bill_files:
            with open(bill_file, 'r') as f:
                bill = json.load(f)
                if bill.get("draft") and bill["draft"].get("requesterType") == "AGENCY":
                    agency_ids.add(bill["draft"]["requesterId"])
    
    return list(agency_ids)

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
            print(f"Failed to fetch agency {agency_id}: {response.status_code}")
            return {"id": agency_id, "agency": f"Unknown Agency {agency_id}"}
    except Exception as e:
        print(f"Error fetching agency {agency_id}: {e}")
        return {"id": agency_id, "agency": f"Error: {e}"}

def main():
    # Create download directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Load agency IDs from bill data
    agency_ids = load_bill_data()
    print(f"Found {len(agency_ids)} unique agency IDs")
    
    # Fetch agency details
    agencies = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_id = {executor.submit(fetch_agency, agency_id): agency_id for agency_id in agency_ids}
        for future in as_completed(future_to_id):
            agency_id = future_to_id[future]
            try:
                agency = future.result()
                agencies[agency_id] = agency["agency"]
            except Exception as e:
                print(f"Error processing agency {agency_id}: {e}")
    
    # Format data as requested
    agency_lookup = {}
    for agency_id, agency_name in agencies.items():
        agency_lookup[agency_id] = {
            "id": agency_id,
            "agency": agency_name
        }
    
    # Save to JSON file
    with open(AGENCIES_LOOKUP_FILE, 'w') as f:
        json.dump(agency_lookup, f, indent=2)
    
    print(f"Agency lookup saved to {AGENCIES_LOOKUP_FILE} with {len(agency_lookup)} agencies")

if __name__ == "__main__":
    main()