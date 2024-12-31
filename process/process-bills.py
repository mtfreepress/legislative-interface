import requests
import json
import os
from datetime import datetime

# 2023
# session = 20231

# 20251 is apparently `2` now
session = 2

# date formatting function
def formatted_date(date_string, default="undefined"):
    if not date_string: 
        return default
    try:
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").strftime("%m/%d/%Y")
    except (ValueError, AttributeError):
        return default

# generate sponsor district from "House"/"Senate" + district number
def format_sponsor_district(bill_type, district_number):
    if not district_number or district_number == "undefined":
        return "undefined"
    if bill_type in ["HB", "HJ", "HR"]:
        prefix = "HD"
    elif bill_type in ["SB", "SJ", "SR"]:
        prefix = "SD"
    else:
        prefix = ""
    return f"{prefix}{district_number}" if prefix else "undefined"

# fiscal code based on subject description
def map_fiscal_code(subject_description):
    if subject_description == "Appropriations  (see also: State Finance)":
        return "Appropriation"
    elif subject_description in ["Revenue, Local", "Revenue, State"]:
        return "Revenue"
    return ""  # empty string if no match

# safe get function for nested data
def safe_get(d, keys, default="undefined"):
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d

def sanitize_filename(key):
    return key.replace(" ", "").replace("/", "-").replace(".", "")

# load legislator json
with open("../inputs/legislators/legislators.json", "r") as f:
    legislators_data = json.load(f)
    
# create map for lookup by legislatorId
legislator_map = {legislator["id"]: legislator for legislator in legislators_data}

# load bill json
json_file = f"../interface/downloads/raw-{session}-bills.json"
with open(json_file, "r") as f:
    json_data = json.load(f)

processed_bills = []
bills = json_data.get("content", []) 

cleaned_dir = os.path.join(os.getcwd(), "cleaned", f"bills-{session}")
os.makedirs(cleaned_dir, exist_ok=True)

for bill in bills:
    # get bill data
    draft = safe_get(bill, ["id"], {})
    session_id = str(safe_get(bill, ["sessionId"]))
    bill_type_data = bill.get("billType", {})
    bill_type = (bill_type_data.get("code", "") if bill_type_data else "").upper()
    draft_data = safe_get(bill, ["draft"], {})
    draft_number = safe_get(draft_data, ["draftNumber"])
    bill_number = bill.get("billNumber", "undefined")
    bill_actions = bill.get("billActions", [])
    
    if not bill_type or not bill_number:
        continue

    # most recent action
    bill_statuses = draft_data.get("billStatuses", [])
    most_recent_action = bill_statuses[-1] if bill_statuses else {}
    last_action_time = formatted_date(safe_get(most_recent_action, ["timeStamp"]))
    last_bill_status = safe_get(most_recent_action, ["billStatusCode"])
    sponsor_roles = bill.get("primarySponsorBillRoles", [])
    sponsor_data = safe_get(sponsor_roles[0], ["legislator"], {}) if sponsor_roles else {}

    # get sponsor information via sponsorId 
    sponsor_id = bill.get("sponsorId", None)
    sponsor = legislator_map.get(sponsor_id, {})
    party = safe_get(sponsor, ["politicalParty", "name"])
    sponsor_district = format_sponsor_district(bill_type, safe_get(sponsor, ["district", "number"]))

    # bill details
    chamber = "house" if bill_type == "HB" else "senate" if bill_type == "SB" else "undefined"
    requester_id = draft_data.get("requesterId", [])
    requester = legislator_map.get(requester_id)
    requester_first_name = requester.get("firstName")
    requester_last_name = requester.get("lastName")
    bill_requester = f"{requester_first_name} {requester_last_name}"

    subjects = [
        {
            "subject": safe_get(raw_subjects, ["subjectCode", "description"]),
            "fiscalCode": map_fiscal_code(safe_get(raw_subjects, ["subjectCode", "description"])),
            "voteReq": safe_get(raw_subjects, ["subjectCode", "voteMajorityType"]),
        }
        for raw_subjects in draft_data.get("subjects", [])
    ]
    vote_requirements = list({subject.get("voteReq", "undefined") for subject in subjects})
    
    # handle dates
    most_recent_date_raw = safe_get(most_recent_action, ["date"])
    most_recent_date_formatted = formatted_date(most_recent_date_raw)

    # build bill json
    bill_key = f"{bill_type} {bill_number}" if bill_type and bill_number else f"{draft_number}"
    processed_bill = {
        "key": bill_key,
        "session": session_id,
        "billPageUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=sum",
        "billTextUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=bill",
        "billPdfUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=bill",
        "lc": draft_number,
        "title": draft_data.get("shortTitle", "undefined"),
        "sponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
        "sponsorParty": party,
        "sponsorDistrict": sponsor_district,
        "statusDate": last_action_time,
        "lastAction": last_bill_status.get("name", "undefined"),
        "billStatus": safe_get(last_bill_status, ["billProgressCategory", "description"]),
        "fiscalNotesListUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=amend",
        "legalNoteUrl": "undefined",
        "amendmentListUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=amend",
        "draftRequestor": None, # TODO: See if we have any of these in the data
        "billRequestor": bill_requester,
        "primarySponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
        "subjects": subjects,
        "voteRequirements": vote_requirements,
        "deadlineCategory": safe_get(bill, ["deadlineCategory", "name"]),
        "transmittalDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "transmittalDate"])),
        "amendedReturnDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "returnDate"])),
    }

    sanitized_key = sanitize_filename(processed_bill["key"])
    bill_file_path = os.path.join(cleaned_dir, f"{sanitized_key}-data.json")
    with open(bill_file_path, "w") as bill_file:
        json.dump(processed_bill, bill_file, indent=2)
    # verbose output - not needed in production but handy for debugging
    # print(f"Saved bill '{processed_bill['key']}' to '{bill_file_path}'.")

print(f"All processed bills saved to '{cleaned_dir}'.")
