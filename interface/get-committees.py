import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# load votes and bills
def load_votes_and_bills(session_id):
    votes_dir = os.path.join(BASE_DIR, f"downloads/raw-{session_id}-votes")
    list_bills_file = os.path.join(BASE_DIR, f"list-bills-{session_id}.json")
    with open(list_bills_file, 'r') as file:
        bills = json.load(file)
    return votes_dir, bills

# extract unique committee ids
def extract_unique_committee_ids(votes_dir, bills):
    committee_ids = set()
    for bill in bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']
        vote_file_path = os.path.join(votes_dir, f"{bill_type}-{bill_number}-raw-votes.json")
        if os.path.exists(vote_file_path):
            with open(vote_file_path, 'r') as file:
                vote_data = json.load(file)
            for entry in vote_data:
                draft = entry.get('bill', {}).get('draft', {})
                bill_statuses = draft.get('billStatuses', [])
                for status in bill_statuses:
                    committee_id = status.get('standingCommitteeId')
                    if committee_id is not None:
                        committee_ids.add(committee_id)
    return sorted(committee_ids)

# call api for a single committee id
def call_committee_api(committee_id, session_id):
    url = 'https://api.legmt.gov/committees/v1/standingCommittees/search?limit=1&offset=0'
    payload = {
        "standingCommitteeIds": [committee_id],
        "legislatureIds": [session_id]
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# save extracted data to file
def save_to_file(data, session_id):
    output_file = os.path.join(BASE_DIR, f"downloads/committees-{session_id}.json")
    with open(output_file, 'w') as file:
        json.dump(data, file, indent=4)

    # print(f"saved data for session {session_id} to {output_file}")



# extract required fields
def extract_required_fields(api_response):
    content = api_response.get('content', [])
    if content:
        entry = content[0]
        return {
            "id": entry["id"],
            "committeeDetails": entry["committeeDetails"]["committeeCode"]
        }
    return None

# main process
def main(session_id):
    votes_dir, bills = load_votes_and_bills(session_id)
    committee_ids = extract_unique_committee_ids(votes_dir, bills)
    # print(f"unique committee ids: {committee_ids}")

    all_data = []
    for committee_id in committee_ids:
        api_response = call_committee_api(committee_id, session_id)
        # print(api_response)
        extracted_data = extract_required_fields(api_response)
        if extracted_data:
            all_data.append(extracted_data)

    save_to_file(all_data, session_id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process standing committee ids")
    parser.add_argument('session_id', type=int, help="legislative session id")
    args = parser.parse_args()
    main(args.session_id)