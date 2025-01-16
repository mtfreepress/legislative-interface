import os
import json
from datetime import datetime
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

votes_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-votes")
bills_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-bills")
list_bills_file = os.path.join(BASE_DIR, "../list-bills-2.json")
legislators_file = os.path.join(BASE_DIR, "../inputs/legislators/legislators.json")
committees_file = os.path.join(BASE_DIR, "downloads/committees-2.json")  # Path to the committees file
output_dir = os.path.join(BASE_DIR, "downloads/matched-{session_id}-votes")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Match votes and bill statuses.")
    parser.add_argument("session_id", type=str, help="Legislative session ID")
    return parser.parse_args()

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def formatted_date(date_string, default="undefined"):
    if not date_string:
        return default
    try:
        # split to get just the date part and format it
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").strftime("%m/%d/%Y")
    except (ValueError, AttributeError):
        # handle invalid date strings
        return default

def main():
    args = parse_arguments()
    session_id = args.session_id

    list_bills = load_json(list_bills_file)
    legislators = {leg['id']: leg for leg in load_json(legislators_file)}
    committees = load_json(committees_file)  # committees data

    # lookup for committees by their id
    committee_lookup = {committee['id']: committee['committeeDetails'] for committee in committees}

    os.makedirs(output_dir.format(session_id=session_id), exist_ok=True)

    for bill in list_bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        vote_file_path = os.path.join(votes_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-votes.json")
        bill_file_path = os.path.join(bills_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-bill.json")

        if not os.path.exists(vote_file_path) or not os.path.exists(bill_file_path):
            print(f"Missing files for {bill_type} {bill_number}. Skipping.")
            continue

        votes_data = load_json(vote_file_path)
        bill_data = load_json(bill_file_path)

        # counters for action IDs
        bill_action_counters = {}
        bill_key = f"{bill_type}{bill_number}"
        if bill_key not in bill_action_counters:
            bill_action_counters[bill_key] = 1

        actions = []

        # sort by action/timestamp
        bill_statuses = bill_data.get('draft', {}).get('billStatuses', [])
        bill_statuses.sort(key=lambda x: x.get('timeStamp'))  # Sort by timestamp (oldest first)

        # process each billStatus entry and generate actions
        for bill_status in bill_statuses:
            action_id = f"{bill_key}-{bill_action_counters[bill_key]:04d}"
            bill_action_counters[bill_key] += 1
            
            action_type = bill_status.get("billStatusCode", {})
            action_description = action_type.get("name", "undefined")
            action_category = (
                action_type.get("progressCategory", {})
                .get("description", "undefined")
                if action_type.get("progressCategory") is not None
                else "undefined"
            )
            action_date = formatted_date(bill_status.get("timeStamp"))
            yes_votes = 0
            no_votes = 0
            vote_seq = "undefined"

            action_data = {
                "id": action_id,
                "bill": f"{bill_type} {bill_number}",
                "date": action_date,
                "description": action_description,
                "posession": "house" if bill_type.startswith("H") else "senate",
                "committee": None,  # Initialize as None
                "actionUrl": None,
                "recordings": [],
                "transcriptUrl": None,
                "key": action_description,
            }

            # match with votes first
            matched_votes = []
            
            for item in votes_data:
                bill_status_data = item.get('billStatus')
                if bill_status_data and bill_status_data.get('id') == bill_status.get('id'):
                    house_sequence = item["systemId"]
                    vote_seq = f"{house_sequence['chamber'][0]}{house_sequence['sequence']}"
                    
                    # TODO: This appears to be working but need to make sure once more data is in the system
                    standing_committee_id = bill_status_data.get('standingCommitteeId')
                    if standing_committee_id and standing_committee_id in committee_lookup:
                        committee_details = committee_lookup[standing_committee_id]
                        committee_name = committee_details.get('name', 'undefined')
                        if committee_name.startswith("(H)"):
                            action_data["voteChamber"] = "House"
                            committee_name = committee_name[4:].strip()
                        elif committee_name.startswith("(S)"):
                            action_data["voteChamber"] = "Senate" 
                            committee_name = committee_name[4:].strip()
                        action_data["committee"] = committee_name

                    gop_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}
                    dem_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}

                    # process legislator votes
                    for vote in item.get('legislatorVotes', []):
                        legislator_id = vote.get('legislatorId')
                        if legislator_id is None:
                            print(f"Skipping vote without legislatorId: {vote}")
                            continue

                        legislator = legislators.get(legislator_id)
                        if legislator:
                            vote_type = vote.get('voteType', "Unknown")[0]
                            political_party_code = legislator.get("politicalParty", {}).get("code", "Unknown")

                            if vote_type == "Y":
                                yes_votes += 1
                            elif vote_type == "N":
                                no_votes += 1

                            if political_party_code == "R":
                                gop_count[vote_type] = gop_count.get(vote_type, 0) + 1
                            elif political_party_code == "D":
                                dem_count[vote_type] = dem_count.get(vote_type, 0) + 1

                            district = legislator.get("district", {})
                            district_prefix = "HD" if district.get("chamber") == "HOUSE" else "SD"
                            district_formatted = f"{district_prefix} {district.get('number', 'Unknown')}"

                            matched_votes.append({
                                "option": vote_type,
                                "name": f"{legislator['firstName']} {legislator['lastName']}",
                                "lastName": legislator['lastName'],
                                "party": political_party_code,
                                "locale": legislator.get("city", "Unknown"),
                                "district": district_formatted,
                            })

            if matched_votes:
                action_data["vote"] = {
                    "action": action_data["id"],
                    "bill": action_data["bill"],
                    "date": action_data["date"],
                    "type": "committee" if action_data.get("committee") else "floor",
                    "seqNumber": vote_seq,
                    "voteChamber": house_sequence['chamber'].lower(),
                    "voteUrl": None,
                    "session": session_id,
                    "motion": action_description,
                    "thresholdRequired": "simple",
                    "count": {"Y": yes_votes, "N": no_votes},
                    "gopCount": gop_count,
                    "demCount": dem_count,
                    "motionPassed": yes_votes > no_votes,
                    "gopSupported": gop_count["Y"] > gop_count["N"],
                    "demSupported": dem_count["Y"] > dem_count["N"],
                    "votes": matched_votes,
                }
            else:
                action_data["vote"] = None

            actions.append(action_data)

        # write actions to output file
        output_file_path = os.path.join(output_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-matched-actions.json")
        with open(output_file_path, "w") as f:
            json.dump(actions, f, indent=2)

if __name__ == "__main__":
    main()
