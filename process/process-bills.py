import argparse
import json
import os
from datetime import datetime

# formatted_date function remains unchanged
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

# create a function to process bills with sessionId as an argument
def process_bills(session_id):
    # determine the script's directory
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # load legislator json (adjust the path to be relative to the script)
    legislators_file = os.path.join(script_dir, "../inputs/legislators/legislators.json")
    with open(legislators_file, "r") as f:
        legislators_data = json.load(f)

    # create map for lookup by legislatorId
    legislator_map = {legislator["id"]: legislator for legislator in legislators_data}

    # Load agencies data
    agencies_file = os.path.join(script_dir, "../interface/agencies.json")
    agencies_map = {}
    if os.path.exists(agencies_file):
        with open(agencies_file, "r") as f:
            agencies_data = json.load(f)
        agencies_map = {agency["id"]: agency for agency in agencies_data}

    # Load committees data
    committees_file = os.path.join(script_dir, "../interface/committees.json")
    committees_map = {}
    if os.path.exists(committees_file):
        with open(committees_file, "r") as f:
            committees_data = json.load(f)
        committees_map = {committee["id"]: committee for committee in committees_data}

    # load bill json (adjust the path to be relative to the script)
    json_file = os.path.join(script_dir, f"../interface/downloads/raw-{session_id}-bills.json")
    with open(json_file, "r") as f:
        json_data = json.load(f)

    # load legal notes json
    legal_notes_file = os.path.join(script_dir, "../interface/legal_notes.json")
    with open(legal_notes_file, "r") as f:
        legal_notes_data = json.load(f)
    legal_notes_set = {(note["billType"], note["billNumber"]) for note in legal_notes_data}

    fiscal_notes_file = os.path.join(script_dir, "../interface/fiscal_notes.json")
    with open(fiscal_notes_file, "r") as f:
        fiscal_notes_data = json.load(f)
    fiscal_notes_set = {(note["billType"], note["billNumber"]) for note in fiscal_notes_data}

    veto_letters_file = os.path.join(script_dir, "../interface/veto_letter.json")
    with open(veto_letters_file, "r") as f:
        veto_letters_data = json.load(f)
    veto_letters_set = {(note["billType"], note["billNumber"]) for note in veto_letters_data}

    bill_text_pdf_file = os.path.join(script_dir, "../interface/bill_pdfs.json")
    with open(bill_text_pdf_file, "r") as f:
        bill_text_pdf_data = json.load(f)
    bill_text_pdf_set = {(pdf["billType"], pdf["billNumber"]) for pdf in bill_text_pdf_data}

    processed_bills = []
    bills = json_data.get("content", [])

    # define the cleaned directory (adjust the path to be relative to the script)
    cleaned_dir = os.path.join(script_dir, "cleaned", f"bills-{session_id}")
    os.makedirs(cleaned_dir, exist_ok=True)

    for bill in bills:
        # get bill data
        draft = safe_get(bill, ["id"], {})
        bill_type_data = bill.get("billType", {})
        bill_type = (bill_type_data.get("code", "") if bill_type_data else "").upper()
        bill_description = bill_type_data.get("description", "undefined") if bill_type_data else "undefined"
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

        # Determine the bill requester based on requesterType and requesterId
        requester_id = draft_data.get("requesterId")
        requester_type = draft_data.get("requesterType", "")
        bill_requester = "undefined"

        # Convert requester_id to string for lookups
        requester_id_str = str(requester_id) if requester_id is not None else ""

        # Load all requester lookup files from the new directory
        lookup_dir = os.path.join(script_dir, "../interface/requester-lookup")

        # Load agency lookup
        agencies_lookup_file = os.path.join(lookup_dir, "agencies-lookup.json")
        agencies_lookup = {}
        if os.path.exists(agencies_lookup_file):
            try:
                with open(agencies_lookup_file, 'r') as f:
                    agencies_lookup = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing agencies lookup file: {agencies_lookup_file}")

        # Load legislators lookup
        legislators_lookup_file = os.path.join(lookup_dir, "legislators-lookup.json")
        legislators_lookup = {}
        if os.path.exists(legislators_lookup_file):
            try:
                with open(legislators_lookup_file, 'r') as f:
                    legislators_lookup = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing legislators lookup file: {legislators_lookup_file}")

        # Load standing committees lookup
        standing_committees_lookup_file = os.path.join(lookup_dir, "standing-committees-lookup.json")
        standing_committees_lookup = {}
        if os.path.exists(standing_committees_lookup_file):
            try:
                with open(standing_committees_lookup_file, 'r') as f:
                    standing_committees_lookup = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing standing committees lookup file: {standing_committees_lookup_file}")

        # Load non-standing committees lookup
        non_standing_committees_lookup_file = os.path.join(lookup_dir, "non-standing-committees-lookup.json")
        non_standing_committees_lookup = {}
        if os.path.exists(non_standing_committees_lookup_file):
            try:
                with open(non_standing_committees_lookup_file, 'r') as f:
                    non_standing_committees_lookup = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing non-standing committees lookup file: {non_standing_committees_lookup_file}")

        # Set bill requester based on type and ID
        if requester_type == "LEGISLATOR" and requester_id_str in legislators_lookup:
            bill_requester = legislators_lookup[requester_id_str].get("legislatorName", "Unknown Legislator")
        elif requester_type == "AGENCY":
            # Use byRequestOfId if available
            by_request_of_id = None
            if "byRequestOfs" in draft_data:
                by_request_of_id = draft_data["byRequestOfs"][0].get("byRequestOfId")
            if by_request_of_id and str(by_request_of_id) in agencies_lookup:
                bill_requester = agencies_lookup[str(by_request_of_id)].get("agency", "Unknown Agency")
            elif requester_id_str in agencies_lookup:
                bill_requester = agencies_lookup[requester_id_str].get("agency", "Unknown Agency")
            else:
                bill_requester = "Unknown Agency"
        elif requester_type == "STANDING_COMMITTEE" and requester_id_str in standing_committees_lookup:
            bill_requester = standing_committees_lookup[requester_id_str].get("committee", "Unknown Committee")
        elif requester_type == "NON_STANDING_COMMITTEE" and requester_id_str in non_standing_committees_lookup:
            bill_requester = non_standing_committees_lookup[requester_id_str].get("committee", "Unknown Committee")
        elif requester_id:
            # Unknown requester type but we have an ID
            bill_requester = f"Unknown Requester Type: {requester_type} (ID: {requester_id})"

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

        # check if the bill has a legal note
        has_legal_note = (bill_type, bill_number) in legal_notes_set
        has_fiscal_note = (bill_type, bill_number) in fiscal_notes_set
        has_veto_letter = (bill_type, bill_number) in veto_letters_set

        # bill should always have billTextPdf but check just in case
        has_bill_text_pdf = (bill_type, bill_number) in bill_text_pdf_set

        # build bill json
        bill_key = f"{bill_type} {bill_number}" if bill_type and bill_number else f"{draft_number}"
        hypen_bill_key = f"{bill_type.lower()}-{bill_number}" if bill_type and bill_number else f"{draft_number}"
        expanded_name = f"{bill_description} {bill_number}" if bill_description and bill_number else "undefined"

        processed_bill = {
            "key": bill_key,
            "identifierLong": expanded_name,
            "session": session_id,
            "billPageUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=sum",
            "billTextUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=bill",
            ## this is used on the front end for the PDF
            "billPdfUrl": f"/bills/bill-text/{hypen_bill_key}" if has_bill_text_pdf else None,
            "lc": draft_number,
            "title": draft_data.get("shortTitle", "undefined"),
            "sponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
            "sponsorParty": party,
            "sponsorDistrict": sponsor_district,
            "statusDate": last_action_time,
            "lastAction": last_bill_status.get("name", "undefined"),
            "billStatus": safe_get(last_bill_status, ["billProgressCategory", "description"]),
            "fiscalNotesListUrl": f"/bills/fiscal-note/{hypen_bill_key}" if has_fiscal_note else None,
            "legalNoteUrl": f"/bills/legal-note/{hypen_bill_key}" if has_legal_note else None,
            "governorVetoLetterUrl": f"/bills/veto-letter/{hypen_bill_key}" if has_veto_letter else None,
            "amendmentListUrl": f"https://bills.legmt.gov/#/laws/bill/{session_id}/{draft_number}?open_tab=amend",
            "draftRequestor": None,  # TODO: See if we have any of these in the data
            "billRequestor": bill_requester,
            "primarySponsor": f"{safe_get(sponsor, ['firstName'])} {safe_get(sponsor, ['lastName'])}",
            "subjects": subjects,
            "voteRequirements": vote_requirements,
            "deadlineCategory": safe_get(bill, ["deadlineCategory", "name"]),
            "transmittalDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "transmittalDate"])),
            "amendedReturnDeadline": formatted_date(safe_get(bill, ["deadlineCategory", "returnDate"])),
        }

        # Add the processed bill to our list
        processed_bills.append(processed_bill)
        
        # Save individual bill file
        bill_file_path = os.path.join(cleaned_dir, f"{bill_type}-{bill_number}-data.json")
        with open(bill_file_path, "w") as f:
            json.dump(processed_bill, f, indent=2)
    
    # Save all bills to a single file
    all_bills_path = os.path.join(script_dir, "cleaned", f"all-bills-{session_id}.json")
    with open(all_bills_path, "w") as f:
        json.dump(processed_bills, f, indent=2)
    
    print(f"Processed {len(processed_bills)} bills for session {session_id}")
    return processed_bills

# main function to handle argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process bills by session ID")
    parser.add_argument("sessionId", help="Session ID for processing bills")
    args = parser.parse_args()

    process_bills(args.sessionId)