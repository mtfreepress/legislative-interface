import os
import json
import re
import argparse
from datetime import datetime
from collections import defaultdict

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def save_json_file(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

def get_committee_time(time_str):
    if not time_str:
        return ""
    
    # Simple heuristic for morning/afternoon classification
    time_match = re.search(r'(\d+):(\d+)\s*(AM|PM)', time_str, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        am_pm = time_match.group(3).upper()
        
        if am_pm == 'AM' or (am_pm == 'PM' and hour == 12):
            return 'morning'
        else:
            return 'afternoon'
    
    return ""

def get_committee_type(committee_name):
    # Simple classification based on committee name
    fiscal_keywords = ['appropriations', 'finance', 'budget', 'tax', 'revenue']
    
    for keyword in fiscal_keywords:
        if keyword in committee_name.lower():
            return 'fiscal'
    
    return 'policy'

def process_bill_actions(actions_dir, session_id, committee_keys):
    """Process bill actions to compute committee statistics"""
    # Initialize data structures
    committee_bills = defaultdict(set)
    committee_bill_actions = defaultdict(list)
    committee_stats = defaultdict(lambda: {
        "billsWithdrawn": set(),
        "billsReferredElsewhere": set(),
        "billsHeard": set(),
        "billsScheduled": set(),
        "billsScheduledByDay": defaultdict(list),
        "billsFailed": set(),
        "billsAdvanced": set(),
        "billsBlasted": set()
    })
    
    
    # Get today's date for scheduling calculations
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Process each bill's actions
    actions_path = os.path.join(actions_dir, f"actions-{session_id}")
    if not os.path.exists(actions_path):
        print(f"Warning: Actions directory {actions_path} not found!")
        return {}
    
    for file_name in os.listdir(actions_path):
        if not file_name.endswith('-actions.json'):
            continue
            
        bill_id = file_name.replace('-actions.json', '')
        bill_actions = load_json_file(os.path.join(actions_path, file_name))
        
        # Process each action
        for action in bill_actions:
            committee_id = action.get('committee_id')
            if not committee_id:
                continue
                
            # Find which committee key this ID corresponds to
            committee_key = None
            for key, id_val in committee_keys.items():
                if id_val == committee_id:
                    committee_key = key
                    break
                    
            if not committee_key:
                continue
                
            # Add bill to this committee's bills
            bill = action.get('bill').replace(' ', '')  # Remove space between bill type and number
            committee_bills[committee_key].add(bill)
            committee_bill_actions[committee_key].append(action)
            
            # Check for specific action types
            description = action.get('description', '').lower()
            action_date_str = action.get('date', '')
            action_date = None
            try:
                # Parse date in MM/DD/YYYY format
                action_date = datetime.strptime(action_date_str, '%m/%d/%Y')
            except:
                pass
            
            # Process withdrawals
            if 'withdrawn' in description:
                committee_stats[committee_key]["billsWithdrawn"].add(bill)
                
            # Process hearings
            if 'hearing' in description:
                if action_date and action_date >= today:
                    committee_stats[committee_key]["billsScheduled"].add(bill)
                    committee_stats[committee_key]["billsScheduledByDay"][action_date_str].append(bill)
                else:
                    committee_stats[committee_key]["billsHeard"].add(bill)
                    
            # Process bill outcomes
            if any(term in description for term in ['tabled', 'failed']):
                committee_stats[committee_key]["billsFailed"].add(bill)
                
            if any(term in description for term in ['passed', 'concurred']):
                committee_stats[committee_key]["billsAdvanced"].add(bill)
                
            if 'blast' in description:
                committee_stats[committee_key]["billsBlasted"].add(bill)
                
            if 'referred to committee' in description and committee_bills[committee_key]:
                # This is a re-referral to another committee
                # We'll track this for bills that moved from one committee to another
                for other_key in committee_bills:
                    if other_key != committee_key and bill in committee_bills[other_key]:
                        committee_stats[other_key]["billsReferredElsewhere"].add(bill)
    
    # Calculate unscheduled bills and awaiting vote bills
    for committee_key in committee_bills:
        stats = committee_stats[committee_key]
        bills = committee_bills[committee_key]
        
        # Calculate unscheduled bills - remove referred elsewhere from the exclusion list
        stats["billsUnscheduled"] = bills - stats["billsHeard"] - stats["billsScheduled"] - \
                                  stats["billsWithdrawn"]
        
        # Calculate awaiting vote bills - remove referred elsewhere from the exclusion list
        stats["billsAwaitingVote"] = stats["billsHeard"] - stats["billsFailed"] - \
                                    stats["billsAdvanced"] - stats["billsBlasted"] - \
                                    stats["billsWithdrawn"]
    
    # Convert to output format
    result = {}
    for committee_key, stats in committee_stats.items():
        result[committee_key] = {
            "bills": list(committee_bills[committee_key]),
            "billCount": len(committee_bills[committee_key]),
            "billsWithdrawn": list(stats["billsWithdrawn"]),
            "billsUnscheduled": list(stats["billsUnscheduled"]),
            "billsScheduled": list(stats["billsScheduled"]),
            "billsScheduledByDay": [{"day": day, "bills": bills} for day, bills in stats["billsScheduledByDay"].items()],
            "billsAwaitingVote": list(stats["billsAwaitingVote"]),
            "billsFailed": list(stats["billsFailed"]),
            "billsAdvanced": list(stats["billsAdvanced"]),
            "billsBlasted": list(stats["billsBlasted"])
        }
    
    return result

def process_committees(session_id):
    # Define paths relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    committees_dir = os.path.join(script_dir, '../interface/downloads/all-committees-2')
    legislators_file = os.path.join(script_dir, '../interface/downloads/legislators/legislators.json')
    roster_file = os.path.join(script_dir, '../interface/downloads/legislators/legislator-roster-2025.json')
    actions_dir = os.path.join(script_dir, '../process/cleaned')
    output_file = os.path.join(script_dir, '../interface/committees.json')
    
    # Load legislators data (API data)
    legislators = load_json_file(legislators_file)
    legislators_by_id = {leg['id']: leg for leg in legislators}
    
    # Load legislator roster (with locale information)
    roster = load_json_file(roster_file)
    roster_by_name = {}
    
    for member in roster:
        full_name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
        roster_by_name[full_name.strip()] = member
    
    # Map committee keys to their IDs for action processing
    committee_keys_to_ids = {}
    
    # Process committees
    committees = []
    
    for filename in os.listdir(committees_dir):
        if not filename.endswith('.json'):
            continue
            
        committee_key = os.path.splitext(filename)[0]
        committee_path = os.path.join(committees_dir, filename)
        committee_data = load_json_file(committee_path)
        
        # Store committee ID for action processing
        committee_keys_to_ids[committee_key] = committee_data['id']
        
        # Extract committee name from the committeeCode
        committee_name = committee_data['committeeDetails']['committeeCode']['name']
        
        # Clean up the committee name (remove chamber prefix in parentheses)
        clean_name = re.sub(r'^\((H|S)\)\s*', '', committee_name).strip()
        
        # Process chamber
        if "Joint" in clean_name:
            chamber = "joint"
            # joint committees, keep the name as is (without adding prefix)
            formatted_name = clean_name
        else:
            if committee_data['chamber'] == 'HOUSE':
                chamber = 'house'
                formatted_name = f"House {clean_name}"
            else:
                chamber = 'senate'
                formatted_name = f"Senate {clean_name}"
        
        # Process time
        default_time = committee_data['committeeDetails'].get('defaultTime', None)
        time = get_committee_time(default_time)
        
        # Process committee type
        committee_type = get_committee_type(clean_name)

        roster_lookup = {}
    
        for member in roster:
            # Create lookup by full name
            full_name = f"{member.get('first_name', '')} {member.get('last_name', '')}"
            roster_lookup[full_name.strip()] = member
            
            # Also create lookup by last name only for fallback
            last_name = member.get('last_name', '')
            if last_name:
                if last_name not in roster_lookup:
                    roster_lookup[last_name] = member
        
        # Process members
        members = []
        for membership in committee_data['memberships']:
            legislator_id = membership['legislatorId']
            if legislator_id not in legislators_by_id:
                print(f"Warning: Legislator ID {legislator_id} not found!")
                continue
                
            legislator = legislators_by_id[legislator_id]
            role = membership['type']['name']
            
            # Get party
            party = legislator.get('politicalParty', {}).get('code', '')
            
            # Get full name
            first_name = legislator.get('firstName', '')
            middle_name = legislator.get('middleName', '')
            last_name = legislator.get('lastName', '')
            
            full_name_parts = [first_name]
            if middle_name:
                full_name_parts.append(middle_name)
            full_name_parts.append(last_name)
                
            full_name = ' '.join(part for part in full_name_parts if part)
            
            # Try to get locale from roster using full name
            locale = ""
            if full_name in roster_lookup:
                locale = roster_lookup[full_name].get('locale', '')
            # Try last name if full name doesn't match
            elif last_name in roster_lookup:
                locale = roster_lookup[last_name].get('locale', '')
            
            members.append({
                "name": full_name,
                "party": party,
                "locale": locale,
                "role": role
            })
        
        # Create committee object
        committee = {
            "name": formatted_name,
            "key": committee_key,
            "chamber": chamber,
            "time": time,
            "type": committee_type,
            "bills": [],
            "billCount": 0,
            "billsWithdrawn": [],
            "billsUnscheduled": [],
            "billsScheduled": [],
            "billsScheduledByDay": [],
            "billsAwaitingVote": [],
            "billsFailed": [],
            "billsAdvanced": [],
            "billsBlasted": [],
            "members": members
        }
        
        committees.append(committee)
    
    # Process bill actions to get committee statistics
    committee_stats = process_bill_actions(actions_dir, session_id, committee_keys_to_ids)
    
    # Update committees with bill statistics
    for committee in committees:
        key = committee["key"]
        if key in committee_stats:
            stats = committee_stats[key]
            committee.update(stats)
    
    # Save the processed committees
    save_json_file(committees, output_file)
    print(f"Processed {len(committees)} committees and saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process committee data")
    parser.add_argument("session_id", type=str, help="Session ID for processing bill actions")
    args = parser.parse_args()
    
    process_committees(args.session_id)