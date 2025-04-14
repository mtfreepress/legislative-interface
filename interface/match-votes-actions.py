import os
import json
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

votes_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-votes")
bills_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-bills")
executive_actions_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-executive-actions")
hearings_dir = os.path.join(BASE_DIR, "downloads/committee-{session_id}-hearings")
list_bills_file = os.path.join(BASE_DIR, "../list-bills-2.json")
legislators_file = os.path.join(BASE_DIR, "downloads/legislators/legislators.json")
roster_file = os.path.join(BASE_DIR, "downloads/legislators/legislator-roster-2025.json")
committees_file = os.path.join(BASE_DIR, "downloads/committees-2.json")
output_dir = os.path.join(BASE_DIR, "../process/cleaned/actions-{session_id}")

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
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").strftime("%m/%d/%Y")
    except (ValueError, AttributeError):
        return default

def process_legislator_votes(votes, legislators, roster):
    processed_votes = []
    seen_votes = set()
    for vote in votes:
        legislator_id = vote.get('legislatorId') or vote['membership']['legislatorId']
        vote_type = vote.get('voteType') or vote['committeeVote']
        if legislator_id is None or vote_type is None:
            continue

        legislator = legislators.get(legislator_id)
        if legislator:
            vote_type = vote_type[0]
            political_party_code = legislator.get("politicalParty", {}).get("code", "Unknown")

            district = legislator.get("district", {})
            district_prefix = "HD" if district.get("chamber") == "HOUSE" else "SD"
            district_formatted = f"{district_prefix} {district.get('number', 'Unknown')}"

            # Match based on name to get locale
            first_name = legislator['firstName']
            last_name = legislator['lastName']
            name = f"{first_name} {last_name}"
            roster_entry = next((item for item in roster if item['first_name'] == first_name and item['last_name'] == last_name), None)
            locale = roster_entry.get("locale", "Unknown") if roster_entry else "Unknown"

            vote_key = (legislator_id, vote_type)
            if vote_key not in seen_votes:
                processed_votes.append({
                    "option": vote_type,
                    "name": name,
                    "lastName": last_name,
                    "party": political_party_code,
                    "locale": locale,
                    "district": district_formatted,
                })
                seen_votes.add(vote_key)
    return processed_votes

def match_committee_hearing(bill_status_id, committee_meetings, action_date, action_description=None):
    """Match committee hearings with bill actions."""
    if not committee_meetings:
        return None
        
    # First try exact date match (existing behavior)
    exact_match = None
    
    # Track next scheduled hearing for fallback
    next_hearing = None
    next_hearing_date = None
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for meeting in committee_meetings:
        try:
            # Skip if missing key structures
            if 'committeeMeeting' not in meeting:
                continue
                
            cm = meeting['committeeMeeting']
            if 'standingCommittee' not in cm or 'id' not in cm['standingCommittee']:
                continue
                
            committee_id = cm['standingCommittee']['id']
            if committee_id != bill_status_id:
                continue
                
            # Matching committee found - try to get meeting time
            if 'meetingTime' in cm:
                meeting_time = cm['meetingTime']
                # Convert to date object for comparison
                meeting_date = formatted_date(meeting_time)
                
                # If exact date match, use it immediately
                if meeting_date == action_date:
                    return formatted_date(meeting_time)
                    
                # Otherwise save as potential future meeting
                try:
                    meeting_date_obj = datetime.strptime(meeting_time.split('T')[0], '%Y-%m-%d')
                    if meeting_date_obj >= today:
                        if next_hearing_date is None or meeting_date_obj < next_hearing_date:
                            next_hearing_date = meeting_date_obj
                            next_hearing = formatted_date(meeting_time)
                except Exception:
                    pass
                    
        except Exception:
            continue
    
    # Return next hearing for certain action types (Hearing, Referred to Committee)
    if next_hearing and action_description:
        if "Hearing" in action_description or "Referred to Committee" in action_description:
            return next_hearing
            
    return None

def main():
    args = parse_arguments()
    session_id = args.session_id

    list_bills = load_json(list_bills_file)
    legislators = {leg['id']: leg for leg in load_json(legislators_file)}
    roster = load_json(roster_file)
    committees = load_json(committees_file)

    committee_lookup = {committee['id']: committee['committeeDetails'] for committee in committees}

    os.makedirs(output_dir.format(session_id=session_id), exist_ok=True)

    for bill in list_bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        vote_file_path = os.path.join(votes_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-votes.json")
        bill_file_path = os.path.join(bills_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-bill.json")
        executive_actions_file_path = os.path.join(executive_actions_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-executive-actions.json")
        hearings_file_path = os.path.join(hearings_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-committee-hearings.json")

        if not os.path.exists(vote_file_path) or not os.path.exists(bill_file_path):
            continue

        votes_data = load_json(vote_file_path)
        bill_data = load_json(bill_file_path)
        executive_actions_data = load_json(executive_actions_file_path) if os.path.exists(executive_actions_file_path) else []
        committee_meetings = load_json(hearings_file_path) if os.path.exists(hearings_file_path) else []

        bill_action_counters = {}
        bill_key = f"{bill_type}{bill_number}"
        if bill_key not in bill_action_counters:
            bill_action_counters[bill_key] = 1

        actions = []

        bill_statuses = bill_data.get('draft', {}).get('billStatuses', [])
        bill_statuses.sort(key=lambda x: x.get('timeStamp'))

        processed_action_ids = set()

        for bill_status in bill_statuses:
            action_id = f"{bill_key}-{bill_action_counters[bill_key]:04d}"
            bill_action_counters[bill_key] += 1
            
            action_type = bill_status.get("billStatusCode", {})
            action_description = action_type.get("name", "undefined")
            # Determine possession based on action_description
            if action_description.startswith("(H)"):
                possession = "House"
            elif action_description.startswith("(S)"):
                possession = "Senate"
            else:
                possession = "undefined"
            if action_description.startswith("(") and ")" in action_description:
                action_description = action_description.split(")", 1)[1].strip()
            action_category = (
                action_type.get("progressCategory", {})
                .get("description", "undefined")
                if action_type.get("progressCategory") is not None
                else "undefined"
            )
            action_date = formatted_date(bill_status.get("timeStamp"))
            yes_votes = 0
            no_votes = 0
            vote_seq = f"{action_type.get('chamber', 'U')[0]}{action_type.get('billProgressCategory', {}).get('id', '0')}"

            standing_committee_id = bill_status.get('standingCommitteeId')
            committee_name = committee_lookup.get(standing_committee_id, {}).get('name', 'undefined') if standing_committee_id else 'undefined'

            action_data = {
                "id": action_id,
                "bill": f"{bill_type} {bill_number}",
                "date": action_date,
                "description": action_description,
                "possession": possession,
                "committee": committee_name,
                "actionUrl": None,
                "recordings": [],
                "transcriptUrl": None,
                "key": action_description,
                "committeeHearingTime": None
            }

            if standing_committee_id:
                action_data["committeeHearingTime"] = match_committee_hearing(
                    standing_committee_id,
                    committee_meetings,
                    action_date,
                    action_description
                )

            matched_votes = []
            seen_votes = set()
            
            for item in votes_data:
                bill_status_data = item.get('billStatus')
                if bill_status_data and bill_status_data.get('id') == bill_status.get('id'):
                    # skip "Indefinitely Postpone" votes
                    motion = item.get('motion')
                    if motion is not None and 'indefinitely postpone' in motion.lower():
                        continue

                    house_sequence = item["systemId"]
                    vote_seq = f"{house_sequence['chamber'][0]}{house_sequence['sequence']}"
                    
                    standing_committee_id = bill_status_data.get('standingCommitteeId')
                    if standing_committee_id and standing_committee_id in committee_lookup:
                        committee_details = committee_lookup[standing_committee_id]
                        committee_name = committee_details.get('name', 'undefined')
                        if committee_name.startswith("(H)"):
                            action_data["voteChamber"] = "House"
                            committee_name = "House " + committee_name[4:].strip()
                        elif committee_name.startswith("(S)"):
                            action_data["voteChamber"] = "Senate"
                            committee_name = "Senate " + committee_name[4:].strip()
                        action_data["committee"] = committee_name

                    gop_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}
                    dem_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}

                    for vote in process_legislator_votes(item.get('legislatorVotes', []), legislators, roster):
                        vote_key = (vote['name'], vote['option'])
                        if vote_key not in seen_votes:
                            vote_type = vote['option']
                            if vote_type == "Y":
                                yes_votes += 1
                            elif vote_type == "N":
                                no_votes += 1

                            if vote['party'] == "R":
                                gop_count[vote_type] = gop_count.get(vote_type, 0) + 1
                            elif vote['party'] == "D":
                                dem_count[vote_type] = dem_count.get(vote_type, 0) + 1

                            matched_votes.append(vote)
                            seen_votes.add(vote_key)

            for exec_action in executive_actions_data:
                if exec_action.get('billStatusId') == bill_status.get('id'):
                    action_type = bill_status.get("billStatusCode", {})
                    vote_seq = f"{action_type.get('chamber', 'U')[0]}{action_type.get('billProgressCategory', {}).get('id', '0')}"

                    gop_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}
                    dem_count = {"Y": 0, "N": 0, "A": 0, "E": 0, "O": 0}

                    for vote in process_legislator_votes(exec_action.get('legislatorVotes', []), legislators, roster):
                        vote_key = (vote['name'], vote['option'])
                        if vote_key not in seen_votes:
                            vote_type = vote['option']
                            if vote_type == "Y":
                                yes_votes += 1
                            elif vote_type == "N":
                                no_votes += 1

                            if vote['party'] == "R":
                                gop_count[vote_type] = gop_count.get(vote_type, 0) + 1
                            elif vote['party'] == "D":
                                dem_count[vote_type] = dem_count.get(vote_type, 0) + 1

                            matched_votes.append(vote)
                            seen_votes.add(vote_key)

                    standing_committee_id = exec_action.get('standingCommittee', {}).get('id')
                    if standing_committee_id and standing_committee_id in committee_lookup:
                        committee_details = committee_lookup[standing_committee_id]
                        committee_name = committee_details.get('name', 'undefined')
                        if committee_name.startswith("(H)"):
                            action_data["voteChamber"] = "House"
                            committee_name = "House " + committee_name[4:].strip()
                        elif committee_name.startswith("(S)"):
                            action_data["voteChamber"] = "Senate"
                            committee_name = "Senate " + committee_name[4:].strip()
                        action_data["committee"] = f"{action_data['voteChamber']} {committee_name}"

            if matched_votes:
                action_data["vote"] = {
                    "action": action_data["id"],
                    "bill": action_data["bill"],
                    "date": action_data["date"],
                    "type": "committee" if action_data.get("committee") else "floor",
                    "seqNumber": vote_seq,
                    "voteChamber": action_type.get('chamber', 'unknown').lower(),
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

            action_key = (action_data["bill"], action_data["date"], action_data["description"])
            if action_key not in processed_action_ids:
                actions.append(action_data)
                processed_action_ids.add(action_key)

        output_file_path = os.path.join(output_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-actions.json")
        with open(output_file_path, "w") as f:
            json.dump(actions, f, indent=2)

if __name__ == "__main__":
    main()