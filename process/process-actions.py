import json
import os
import argparse
from datetime import datetime
import re

# safe get function for nested data
def safe_get(d, keys, default="undefined"):
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d

# reusable date formatting
def formatted_date(date_string, default="undefined"):
    if not date_string:
        return default
    try:
        # split to get just the date part and format it
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").strftime("%m/%d/%Y")
    except (ValueError, AttributeError):
        # handle invalid date strings
        return default

# match committee hearing date
def match_committee_hearing_date(standing_committee_id, committee_meetings):
    for meeting in committee_meetings:
        if meeting['committeeMeeting']['standingCommittee']['id'] == standing_committee_id:
            return formatted_date(meeting['committeeMeeting']['meetingTime'])
    return None

# load json file
def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

# determine possession based on description prefix
def determine_possession(description):
    posession_search = re.search(r'(?<=\()(C|LC|H|S)(?=\))', description)
    posession_key = posession_search.group(0) if posession_search else 'O'
    posession_map = {
        'C': 'staff',
        'LC': 'staff',
        'H': 'house',
        'S': 'senate',
        'O': 'other'
    }
    return posession_map.get(posession_key, 'other')

# process bills and actions
def process_bills(sessionId):
    # determine the script's directory
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # load json file (adjust the path to be relative to the script)
    json_file = os.path.join(script_dir, f"../interface/downloads/raw-{sessionId}-bills.json")
    with open(json_file, "r") as f:
        json_data = json.load(f)

    # track sequential counters for each bill
    bill_action_counters = {}

    # prepare directory for cleaned actions (relative to the script directory)
    cleaned_dir = os.path.join(script_dir, "cleaned", f"actions-{sessionId}")
    os.makedirs(cleaned_dir, exist_ok=True)

    processed_actions = {}
    bills = json_data.get("content", [])

    # Sort bills alphabetically by bill field (i.e., bill_type and bill_number)
    bills.sort(key=lambda bill: (safe_get(bill, ["billType", "code"], ""), safe_get(bill, ["billNumber"], "")))

    for bill in bills:
        draft = bill.get("draft", {})
        draft_number = draft.get("draftNumber", "undefined")
        bill_type = safe_get(bill, ["billType", "code"], "undefined")
        bill_number = safe_get(bill, ["billNumber"], "undefined")

        # skip bills without both a bill_type and bill_number
        if not bill_type or not bill_number:
            continue

        bill_key = f"{bill_type}{bill_number}" if bill_type and bill_number else f"{draft_number}"
        hyphen_bill_key = f"{bill_type}-{bill_number}" if bill_type and bill_number else f"{draft_number}"
        bill_actions = draft.get("billStatuses")

        # counter for the current bill if not already set
        if bill_key not in bill_action_counters:
            bill_action_counters[bill_key] = 1

        bill_actions_data = []

        # Load committee hearings data for the bill
        hearings_file_path = os.path.join(script_dir, f"../interface/downloads/committee-{sessionId}-hearings/{hyphen_bill_key}-committee-hearings.json")
        committee_meetings = load_json(hearings_file_path) if os.path.exists(hearings_file_path) else []

        for action in bill_actions:
            # get action details
            action_type = action.get("billStatusCode", {})
            action_description = action_type.get("name", "undefined")
            action_category = (
                action_type.get("progressCategory", {})
                .get("description", "undefined")
                if action_type.get("progressCategory") is not None
                else "undefined"
            )
            action_date = formatted_date(action.get("timeStamp"))
            vote_seq = action_type.get("voteSeq", "undefined")
            yes_votes = action_type.get("yesVotes", "undefined")
            no_votes = action_type.get("noVotes", "undefined")

            # Match committee hearing date
            standing_committee_id = action.get("standingCommitteeId")
            hearing_date = match_committee_hearing_date(standing_committee_id, committee_meetings)
            if hearing_date:
                action_date = hearing_date

            # Determine possession based on description prefix
            possession = determine_possession(action_description)

            # Strip parenthesis and leading space from description and key
            if action_description.startswith("(") and ")" in action_description:
                action_description = action_description.split(")", 1)[1].strip()

            # generate unique id for actions
            action_id = f"{bill_key}-{bill_action_counters[bill_key]:04d}"
            bill_action_counters[bill_key] += 1

            action_data = {
                "id": action_id,
                "committee_id": standing_committee_id,
                "bill": f"{bill_type} {bill_number}",
                "date": action_date,
                "yesVotes": yes_votes,
                "noVotes": no_votes,
                "voteSeq": vote_seq,
                "description": action_description,
                "posession": possession,
                "committee": action.get("committee", None),
                "actionUrl": None,
                "recordings": [],
                "transcriptUrl": None,
                "key": action_description,
                "draftRequest": True if action_description.startswith("Draft") else False,
                "vote": None
            }
            bill_actions_data.append(action_data)

        # save the actions data for each bill
        if bill_actions_data:
            actions_file = os.path.join(cleaned_dir, f"{hyphen_bill_key}-actions.json")
            with open(actions_file, "w") as f:
                json.dump(bill_actions_data, f, indent=2)
        # Too Verbose for Prod
            # print(f"Actions for {bill_key} saved to {actions_file}")

    files_in_directory = len([f for f in os.listdir(
        cleaned_dir) if os.path.isfile(os.path.join(cleaned_dir, f))])

    # print(f"\nTotal number of files saved in '{cleaned_dir}': {files_in_directory}")

# main function to handle argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process bills and actions by sessionId")
    parser.add_argument("sessionId", help="Session ID for processing bills")
    args = parser.parse_args()

    process_bills(args.sessionId)