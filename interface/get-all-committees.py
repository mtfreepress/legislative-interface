import os
import json
import requests
import argparse
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch and save committee data by session ID.")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("--legislature-id", type=int, default=2, help="Legislature ID (default: 2)")
    return parser.parse_args()

def fetch_standing_committees(session_id):
    url = f"https://api.legmt.gov/committees/v1/standingCommittees/findBySessionId?sessionId={session_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch standing committees: {response.status_code}")
        return []

def fetch_non_standing_committees(legislature_id):
    url = "https://api.legmt.gov/committees/v1/nonStandingCommittees/search?limit=500&offset=0"
    data = {"legislatureIds": [legislature_id]}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch non-standing committees: {response.status_code}")
        return []

def sanitize_filename(name, chamber=None):
    # Remove parentheses, commas, and & characters, replace spaces with hyphens, and convert to lowercase
    sanitized_name = re.sub(r'[(),&]', '', name).replace(" ", "-").lower()
    # Replace multiple hyphens with a single hyphen
    sanitized_name = re.sub(r'-+', '-', sanitized_name)
    
    if chamber:
        # Remove the 's' or 'h' from the committee names
        if sanitized_name.startswith("s-"):
            sanitized_name = sanitized_name[2:]
        elif sanitized_name.startswith("h-"):
            sanitized_name = sanitized_name[2:]
        # Prefix with 'house-' or 'senate-' based on the chamber
        if chamber == "HOUSE":
            return f"house-{sanitized_name}"
        elif chamber == "SENATE":
            return f"senate-{sanitized_name}"
    
    return sanitized_name

def save_standing_committee(committee, session_id, all_committees):
    committee_name = committee["committeeDetails"]["committeeCode"]["name"]
    chamber = committee["chamber"]
    sanitized_name = sanitize_filename(committee_name, chamber)
    file_path = os.path.join(DOWNLOAD_DIR, f"standing-committees-{session_id}", f"{sanitized_name}.json")
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        json.dump(committee, f, indent=2)
    print(f"Saved standing committee: {file_path}")
    
    # Add key to the committee and append to all_committees list
    committee_with_key = committee.copy()
    committee_with_key["key"] = sanitized_name
    # Move the key field after the id field
    committee_with_key = {k: committee_with_key[k] for k in ["id", "key"] + [k for k in committee_with_key if k not in ["id", "key"]]}
    all_committees.append(committee_with_key)
    
    # Return committee lookup data
    return {
        "id": committee["id"],
        "committee": committee_name
    }

def save_non_standing_committee(committee, legislature_id, all_non_standing_committees):
    committee_name = committee["name"]
    sanitized_name = sanitize_filename(committee_name)
    file_path = os.path.join(DOWNLOAD_DIR, f"non-standing-committees-{legislature_id}", f"{sanitized_name}.json")
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        json.dump(committee, f, indent=2)
    print(f"Saved non-standing committee: {file_path}")
    
    # Add key to the committee and append to all_committees list
    committee_with_key = committee.copy()
    committee_with_key["key"] = sanitized_name
    # Move the key field after the id field
    committee_with_key = {k: committee_with_key[k] for k in ["id", "key"] + [k for k in committee_with_key if k not in ["id", "key"]]}
    all_non_standing_committees.append(committee_with_key)
    
    # Return committee lookup data
    return {
        "id": committee["id"],
        "committee": committee_name
    }

def main():
    args = parse_arguments()
    session_id = args.sessionId
    legislature_id = args.legislature_id

    # Process standing committees
    standing_committees = fetch_standing_committees(session_id)
    all_standing_committees = []
    standing_lookup = {}
    
    for committee in standing_committees:
        lookup_data = save_standing_committee(committee, session_id, all_standing_committees)
        standing_lookup[lookup_data["id"]] = lookup_data
    
    # Save all standing committees to a single file
    all_standing_file_path = os.path.join(DOWNLOAD_DIR, f"all-standing-committees-{session_id}.json")
    with open(all_standing_file_path, "w") as f:
        json.dump(all_standing_committees, f, indent=2)
    print(f"Saved: {all_standing_file_path}")
    
    # Save standing committee lookup
    standing_lookup_file_path = os.path.join(DOWNLOAD_DIR, f"standing-committees-lookup.json")
    with open(standing_lookup_file_path, "w") as f:
        json.dump(standing_lookup, f, indent=2)
    print(f"Saved: {standing_lookup_file_path}")
    
    # Process non-standing committees
    non_standing_committees = fetch_non_standing_committees(legislature_id)
    all_non_standing_committees = []
    non_standing_lookup = {}
    
    for committee in non_standing_committees:
        lookup_data = save_non_standing_committee(committee, legislature_id, all_non_standing_committees)
        non_standing_lookup[lookup_data["id"]] = lookup_data
    
    # Save all non-standing committees to a single file
    all_non_standing_file_path = os.path.join(DOWNLOAD_DIR, f"all-non-standing-committees-{legislature_id}.json")
    with open(all_non_standing_file_path, "w") as f:
        json.dump(all_non_standing_committees, f, indent=2)
    print(f"Saved: {all_non_standing_file_path}")
    
    # Save non-standing committee lookup
    non_standing_lookup_file_path = os.path.join(DOWNLOAD_DIR, f"non-standing-committees-lookup.json")
    with open(non_standing_lookup_file_path, "w") as f:
        json.dump(non_standing_lookup, f, indent=2)
    print(f"Saved: {non_standing_lookup_file_path}")

if __name__ == "__main__":
    main()