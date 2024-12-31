import json
from datetime import datetime
import os

# 2023
# session = 20231

# 2025 uses just `2` for the sessionId
session = 2

# load json file
json_file = f"../interface/downloads/raw-{session}-bills.json"
with open(json_file, "r") as f:
    json_data = json.load(f)

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


# track sequential counters for each bill
bill_action_counters = {}

# prepare directory for cleaned actions
cleaned_dir = os.path.join(os.getcwd(), "cleaned", f"actions-{session}")
os.makedirs(cleaned_dir, exist_ok=True)

# unified directory for actions/bills:
# cleaned_dir = os.path.join(os.getcwd(), "cleaned", f"{session}")
# os.makedirs(cleaned_dir, exist_ok=True)

# process bills and actions
processed_actions = {}
bills = json_data.get("content", [])
for bill in bills:
    draft = bill.get("draft", {})
    draft_number = draft.get("draftNumber", "undefined")
    bill_type = safe_get(bill, ["billType", "code"], "undefined")
    bill_number = safe_get(bill, ["billType", "id"], "undefined")


    # skip bills without both a bill_type and bill_number
    if not bill_type or not bill_number:
        continue

    bill_key = f"{bill_type} {
        bill_number}" if bill_type and bill_number else f"{draft_number}"
    bill_actions = draft.get("billStatuses")


    # counter for the current bill if not already set
    if bill_key not in bill_action_counters:
        bill_action_counters[bill_key] = 0

    bill_actions_data = []

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
        # TODO - Will need to use PDF vote totals maybe? 
        # hard to say since they often just leave fields off entirely when empty so
        # yesVotes/noVotes/voteSeq may be there? :| 
        vote_seq = action.get("voteSeq", "undefined")
        yes_votes = action.get("yesVotes", "undefined")
        no_votes = action.get("noVotes", "undefined")

        # generate unique id for actions
        action_id = f"{bill_key}-{bill_action_counters[bill_key]:04d}"
        bill_action_counters[bill_key] += 1

        action_data = {
            "id": action_id,
            "bill": f"{bill_type} {bill_number}",
            "date": action_date,
            "yesVotes": yes_votes,
            "noVotes": no_votes,
            "voteSeq": vote_seq,
            "description": action_description,
            "posession": "staff",  # TODO: placeholder
            "committee": action.get("committee", None),
            "actionUrl": None,
            "recordings": [],
            "transcriptUrl": None,
            "key": action_description,
            "draftRequest": True if action_description.startswith("Draft") else False,
            # TODO implement vote counts
            "vote": None
        }
        bill_actions_data.append(action_data)

    # save the actions data for each bill
    if bill_actions_data:
        actions_file = f"{cleaned_dir}/{bill_key}-actions.json"
        with open(actions_file, "w") as f:
            json.dump(bill_actions_data, f, indent=2)

        print(f"Actions for {bill_key} saved to {actions_file}")

files_in_directory = len([f for f in os.listdir(
    cleaned_dir) if os.path.isfile(os.path.join(cleaned_dir, f))])

print(f"\nTotal number of files saved in '{cleaned_dir}': {files_in_directory}")
