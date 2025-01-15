import os
import json
from datetime import datetime
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

votes_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-votes")
bills_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-bills")
list_bills_file = os.path.join(BASE_DIR, "../list-bills-2.json")
legislators_file = os.path.join(BASE_DIR, "../inputs/legislators/legislators.json")
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

        # counter for the current bill if not already set
        bill_action_counters = {}
        bill_key = f"{bill_type}{bill_number}"
        if bill_key not in bill_action_counters:
            bill_action_counters[bill_key] = 1

         # generate unique id for actions
        action_id = f"{bill_key}-{bill_action_counters[bill_key]:04d}"
        bill_action_counters[bill_key] += 1

        actions = []

        for item in votes_data:
            bill_status_id = item.get('billStatus', {}).get('id') or item.get('billStatusId')
            action_type = item.get("billStatusCode", {})
            action_description = action_type.get("name", "undefined")
            action_category = (
                action_type.get("progressCategory", {})
                .get("description", "undefined")
                if action_type.get("progressCategory") is not None
                else "undefined"
            )
            action_date = formatted_date(item.get("timeStamp"))
            yes_votes = item.get("yesVotes", 0)
            no_votes = item.get("noVotes", 0)
            vote_seq = item.get("voteSeq", "undefined")

            action_data = {
                "id": action_id,
                "bill": f"{bill_type} {bill_number}",
                "date": action_date,
                "description": action_description,
                "posession": "house" if bill_type.startswith("H") else "senate",
                "committee": item.get("committee", None),
                "actionUrl": None,
                "recordings": [],
                "transcriptUrl": None,
                "key": action_description,
            }

            matched_votes = []
            for bill_status in bill_data.get('draft', {}).get('billStatuses', []):
                if bill_status['id'] == bill_status_id:
                    # match legislator votes with their id
                    for vote in item.get('legislatorVotes', []):
                        legislator_id = vote.get('legislatorId')
                        if legislator_id is None:
                            print(f"Skipping vote without legislatorId: {vote}")
                            continue

                        legislator = legislators.get(legislator_id)
                        if legislator:
                            political_party = legislator.get("politicalParty", {})
                            district = legislator.get("district", {})
                            district_prefix = "HD" if district.get("chamber") == "HOUSE" else "SD"
                            district_formatted = f"{district_prefix} {district.get('number', 'Unknown')}"

                            matched_votes.append({
                                "option": vote.get('voteType', "Unknown")[0],  # E.g., 'Y' or 'N'
                                "name": f"{legislator['firstName']} {legislator['lastName']}",
                                "lastName": legislator['lastName'],
                                "party": political_party.get("code", "Unknown"),
                                "locale": legislator.get("city", "Unknown"),
                                "district": district_formatted,
                            })

            if matched_votes:
                # populate vote structure if it exists
                action_data["vote"] = {
                    "action": action_data["id"],
                    "bill": action_data["bill"],
                    "date": action_data["date"],
                    "type": "committee",  # TODO: Figure this out
                    "seqNumber": vote_seq,
                    "voteChamber": None,
                    "voteUrl": None,
                    "session": session_id,
                    "motion": action_description,
                    "thresholdRequired": "simple",
                    "count": {"Y": yes_votes, "N": no_votes},
                    "gopCount": {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}, # TODO: calculate this
                    "demCount": {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}, # TODO: calculate this
                    "motionPassed": yes_votes > no_votes,
                    "gopSupported": None, # TODO: calculate this
                    "demSupported": None, # TODO: calculate this
                    "votes": matched_votes,
                }
            else:
                # set vote to null if no votes matched
                action_data["vote"] = None

            actions.append(action_data)

        output_file_path = os.path.join(output_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-matched-actions.json")
        with open(output_file_path, "w") as f:
            json.dump(actions, f, indent=2)

if __name__ == "__main__":
    main()