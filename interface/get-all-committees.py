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
    return parser.parse_args()

def fetch_committees(session_id):
    url = f"https://api.legmt.gov/committees/v1/standingCommittees/findBySessionId?sessionId={session_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch committees: {response.status_code}")
        return []

def sanitize_filename(name, chamber):
    # Remove parentheses, commas, and & characters, replace spaces with hyphens, and convert to lowercase
    sanitized_name = re.sub(r'[(),&]', '', name).replace(" ", "-").lower()
    # Replace multiple hyphens with a single hyphen
    sanitized_name = re.sub(r'-+', '-', sanitized_name)
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
    else:
        return sanitized_name

def save_committee(committee, session_id, all_committees):
    committee_name = committee["committeeDetails"]["committeeCode"]["name"]
    chamber = committee["chamber"]
    sanitized_name = sanitize_filename(committee_name, chamber)
    file_path = os.path.join(DOWNLOAD_DIR, f"all-committees-{session_id}", f"{sanitized_name}.json")
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        json.dump(committee, f, indent=2)
    print(f"Saved: {file_path}")
    
    # Add key to the committee and append to all_committees list
    committee_with_key = committee.copy()
    committee_with_key["key"] = sanitized_name
    # Move the key field after the id field
    committee_with_key = {k: committee_with_key[k] for k in ["id", "key"] + [k for k in committee_with_key if k not in ["id", "key"]]}
    all_committees.append(committee_with_key)

def main():
    args = parse_arguments()
    session_id = args.sessionId

    committees = fetch_committees(session_id)
    all_committees = []
    for committee in committees:
        save_committee(committee, session_id, all_committees)
    
    # Save all committees to a single file
    all_committees_file_path = os.path.join(DOWNLOAD_DIR, f"all-committees-{session_id}.json")
    with open(all_committees_file_path, "w") as f:
        json.dump(all_committees, f, indent=2)
    print(f"Saved: {all_committees_file_path}")

if __name__ == "__main__":
    main()