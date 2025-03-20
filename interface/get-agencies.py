import os
import json
import requests
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
BILLS_DIR = os.path.join(BASE_DIR, "..", "raw-2-bills")  # Check parent directory
LOOKUP_DIR = os.path.join(BASE_DIR, "requester-lookup")
AGENCIES_LOOKUP_FILE = os.path.join(LOOKUP_DIR, "agencies-lookup.json")

def load_bill_data():
    """Load bill data either from raw-2-bills.json or individual bill files"""
    agency_ids = set()
    
    # Check multiple possible locations for bill files
    possible_locations = [
        os.path.join(BASE_DIR, "..", "raw-2-bills"),  # Parent directory
        os.path.join(BASE_DIR, "raw-2-bills"),        # Current directory
        os.path.join(DOWNLOAD_DIR, "raw-2-bills")     # Downloads directory
    ]
    
    # First check if we have a consolidated JSON
    raw_bills_file = os.path.join(BASE_DIR, "..", "raw-2-bills.json")
    if os.path.exists(raw_bills_file):
        print(f"Loading bills from {raw_bills_file}")
        with open(raw_bills_file, 'r') as f:
            bills = json.load(f)
            for bill in bills:
                if bill.get("draft") and bill["draft"].get("requesterType") == "AGENCY":
                    agency_ids.add(bill["draft"]["requesterId"])
    else:
        # Try each possible location for individual bill files
        for location in possible_locations:
            if os.path.exists(location):
                print(f"Loading bills from individual files in {location}")
                # Try different patterns to find bill files
                patterns = [
                    os.path.join(location, "*", "*.json"),  # Nested structure
                    os.path.join(location, "*.json"),       # Flat structure
                    os.path.join(location, "*-raw-bill.json")  # Specific naming pattern
                ]
                
                for pattern in patterns:
                    bill_files = glob.glob(pattern)
                    if bill_files:
                        print(f"Found {len(bill_files)} bill files matching {pattern}")
                        for bill_file in bill_files:
                            try:
                                with open(bill_file, 'r') as f:
                                    bill = json.load(f)
                                    if bill.get("draft") and bill["draft"].get("requesterType") == "AGENCY":
                                        agency_ids.add(bill["draft"]["requesterId"])
                            except json.JSONDecodeError:
                                print(f"Error parsing JSON in {bill_file}")
                
                if agency_ids:
                    break  # Stop if we found agency IDs
    
    # Hard-code specific known agency IDs as a fallback
    known_agencies = [130, 143]  # Adding the agency ID from HB-84
    if not agency_ids:
        print("No agency IDs found in bill data. Adding known agency IDs...")
        for agency_id in known_agencies:
            agency_ids.add(agency_id)
    else:
        # Add known agencies even if we found others
        for agency_id in known_agencies:
            if agency_id not in agency_ids:
                print(f"Adding known agency ID: {agency_id}")
                agency_ids.add(agency_id)

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

def fetch_all_agencies():
    """Fetch all agencies directly from the API"""
    url = "https://api.legmt.gov/legislators/v1/organizations/search"
    data = {"limit": 500, "offset": 0, "query": {"types": ["REQUESTING_AGENCY"]}}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            agencies_data = response.json()
            if isinstance(agencies_data, dict) and "agencies" in agencies_data:
                return agencies_data["agencies"]
            return []
        else:
            print(f"Failed to fetch all agencies: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching all agencies: {e}")
        return []

def main():
    # Create download directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    # Create lookup directory if it doesn't exist
    os.makedirs(LOOKUP_DIR, exist_ok=True)
    
    # Load agency IDs from bill data
    agency_ids = load_bill_data()
    print(f"Found {len(agency_ids)} unique agency IDs")
    
    # Fetch agency details
    agencies = {}
    
    # Process individual agency IDs
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_id = {executor.submit(fetch_agency, agency_id): agency_id for agency_id in agency_ids}
        for future in as_completed(future_to_id):
            agency_id = future_to_id[future]
            try:
                agency = future.result()
                agencies[agency_id] = agency["agency"]
            except Exception as e:
                print(f"Error processing agency {agency_id}: {e}")
    
    # If no agencies found, try direct API approach
    if not agencies:
        print("No agencies found from bill data. Fetching all agencies directly...")
        all_agencies = fetch_all_agencies()
        for agency in all_agencies:
            agency_id = agency.get("id")
            if agency_id:
                agencies[agency_id] = agency.get("name", f"Unknown Agency {agency_id}")
    
    # Format data as requested
    agency_lookup = {}
    for agency_id, agency_name in agencies.items():
        agency_lookup[agency_id] = {
            "id": agency_id,
            "agency": agency_name
        }
    
    with open(AGENCIES_LOOKUP_FILE, 'w') as f:
        json.dump(agency_lookup, f, indent=2)
    
    print(f"Agency lookup saved to {AGENCIES_LOOKUP_FILE} with {len(agency_lookup)} agencies")

if __name__ == "__main__":
    main()