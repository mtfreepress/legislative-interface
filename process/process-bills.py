import os
import json
from datetime import datetime

# 2023
# session = 20231
# 2025 for some reason is not 20251
session = 2

# load json file
json_file = f"../interface/downloads/raw-{session}-bills.json"
with open(json_file, "r") as f:
    json_data = json.load(f)

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


def format_sponsor_district(bill_type, district_number):
    if not district_number or district_number == "undefined":
        return "undefined"

    # map bill types to "HD" or "SD"
    if bill_type in ["HB", "HJ", "HR"]:
        prefix = "HD"
    elif bill_type in ["SB", "SJ", "SR"]:
        prefix = "SD"
    else:
        prefix = ""

    return f"{prefix}{district_number}" if prefix else "undefined"


# map fiscal code based on subject description
def map_fiscal_code(subject_description):
    if subject_description == "Appropriations  (see also: State Finance)":
        return "Appropriation"
    elif subject_description in ["Revenue, Local", "Revenue, State"]:
        return "Revenue"
    return ""  # Default to empty string if no match


# sanitize filenames (removing spaces and special characters)
def sanitize_filename(key):
    return key.replace(" ", "").replace("/", "-").replace(".", "")


def safe_get(d, keys, default="undefined"):
    """Safely get a nested dictionary value."""
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d


processed_bills = []
bills = json_data.get("content", [])
print(f"Bills found: {len(bills)}")  

# create cleaned/bills directory if it doesn't exist
cleaned_dir = os.path.join(os.getcwd(), "cleaned", f"bills-{session}")
os.makedirs(cleaned_dir, exist_ok=True)

for bill in bills:
    # get data
    draft = safe_get(bill, ["id"], {})
    session_id = str(safe_get(bill, ["sessionId"]))
    bill_type_data = bill.get("billType", {})
    bill_type = (bill_type_data.get("code", "") if bill_type_data else "").upper()
    draft_data = safe_get(bill, ["draft"], {})
    draft_number = safe_get(draft_data, ["draftNumber"])
    bill_number = bill.get("billNumber", "undefined")
    bill_actions = bill.get("billActions", [])
    
    # filter out bills that don't have both bill_type and bill_number
    if not bill_type or not bill_number:
        continue

    most_recent_action = bill_actions[0] if bill_actions else {}
    action_type = safe_get(most_recent_action, ["actionType"], {})
    sponsor_roles = bill.get("primarySponsorBillRoles", [])
    sponsor_data = safe_get(sponsor_roles[0], ["legislator"], {}) if sponsor_roles else {}

    sponsor = safe_get(sponsor_data, ["lawEntity"], {})
    party = safe_get(sponsor_data, ["politicalParty"], {})
    sponsor_district = format_sponsor_district(bill_type, safe_get(sponsor_data, ["districtNumber"]))

    chamber = "house" if bill_type == "HB" else "senate" if bill_type == "SB" else "undefined"
    requestors = bill.get("requesters", [])
    requestor = safe_get(requestors[0], ["lawEntity", "lastName"]) if requestors else "undefined"

    subjects = [
        {
            "subject": safe_get(subject, ["subject", "description"]),
            "fiscalCode": map_fiscal_code(safe_get(subject, ["subject", "description"])),
            "voteReq": safe_get(subject, ["subject", "voteRequirement"]),
        }
        for subject in bill.get("subjects", [])
    ]
    vote_requirements = list({subject.get("voteReq", "undefined") for subject in subjects})
    
    # handle dates gracefully
    most_recent_date_raw = safe_get(most_recent_action, ["date"])
    most_recent_date_formatted = formatted_date(most_recent_date_raw)

    # determine the bill key
    bill_key = f"{bill_type} {bill_number}" if bill_type and bill_number else f"{draft_number}"

    # build bill json
    processed_bill = {
        "key": bill_key,
        "session": session_id,
        "billPageUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=sum",
        "billTextUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=bill",
        "billPdfUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=bill",
        "lc": draft_number,
        "title": draft_data.get("shortTitle", "undefined"),
        "sponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
        "sponsorParty": safe_get(party, ["partyName"]),
        "sponsorDistrict": sponsor_district,
        "statusDate": formatted_date(safe_get(most_recent_action, ["date"])),
        "lastAction": safe_get(action_type, ["description"]),
        "billStatus": safe_get(action_type, ["progressCategory", "description"]),
        "fiscalNotesListUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=amend",
        "legalNoteUrl": "undefined",
        "amendmentListUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=amend",
        "draftRequestor": None,
        "billRequestor": requestor,
        "primarySponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
        "subjects": subjects,
        "voteRequirements": vote_requirements,
        "deadlineCategory": safe_get(bill, ["deadlineCategory", "name"]),
        "transmittalDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "transmittalDate"])),
        "amendedReturnDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "returnDate"])),
    }

    # save each bill as json file
    sanitized_key = sanitize_filename(processed_bill["key"])
    bill_file_path = os.path.join(cleaned_dir, f"{sanitized_key}-data.json")
    with open(bill_file_path, "w") as bill_file:
        json.dump(processed_bill, bill_file, indent=2)
    print(f"Saved bill '{processed_bill['key']}' to '{bill_file_path}'.")

print(f"All processed bills saved to '{cleaned_dir}'.")
