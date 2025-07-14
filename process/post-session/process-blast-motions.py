# process/process-blast-motions.py
import os
import json
import csv
import argparse
from collections import defaultdict
from datetime import datetime


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


def save_csv_file(data, file_path, headers):
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def get_bill_title(bill_num, session_id):
    """Get the bill title from the bill file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bill_file = os.path.join(script_dir, f"../interface/downloads/raw-{session_id}-bills/{bill_num}-raw-bill.json")
    
    # Try with dash format
    if not os.path.exists(bill_file) and len(bill_num) > 2:
        # Try adding a dash between type and number (HB-123 instead of HB123)
        bill_type = bill_num[:2]
        bill_number = bill_num[2:]
        bill_file = os.path.join(script_dir, f"../interface/downloads/raw-{session_id}-bills/{bill_type}-{bill_number}-raw-bill.json")
    
    if os.path.exists(bill_file):
        bill_data = load_json_file(bill_file)
        # First try to get shortTitle from draft
        if bill_data.get("draft") and bill_data["draft"].get("shortTitle"):
            title = bill_data["draft"]["shortTitle"]
        # Fallback to regular title
        else:
            title = bill_data.get("title", "")
        
        # If it's too long, truncate it
        if len(title) > 100:
            title = title[:97] + "..."
        return title
    return "Title not available"

def get_bill_sponsor_info(bill_num, session_id):
    """Get the bill sponsor and party information from the bill file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bill_file = os.path.join(script_dir, f"../interface/downloads/raw-{session_id}-bills/{bill_num}-raw-bill.json")
    
    # Try with dash format
    if not os.path.exists(bill_file) and len(bill_num) > 2:
        # Try adding a dash between type and number (HB-123 instead of HB123)
        bill_type = bill_num[:2]
        bill_number = bill_num[2:]
        bill_file = os.path.join(script_dir, f"../interface/downloads/raw-{session_id}-bills/{bill_type}-{bill_number}-raw-bill.json")
    
    sponsor_name = "Unknown"
    sponsor_party = "Unknown"
    sponsor_type = "Legislator"
    
    if os.path.exists(bill_file):
        bill_data = load_json_file(bill_file)
        
        # Get sponsor information
        # Try to get sponsor ID first
        sponsor_id = bill_data.get("sponsorId")
        
        # Check requester type to determine sponsor type
        requester_type = bill_data.get("draft", {}).get("requesterType", "")
        if requester_type == "AGENCY":
            sponsor_type = "Agency"
            sponsor_party = "Agency"
            # Try to get agency name from byRequestOfs
            agency_name = None
            by_request_ofs = bill_data.get("draft", {}).get("byRequestOfs", [])
            if by_request_ofs and len(by_request_ofs) > 0:
                agency_name = "Agency Request"
            sponsor_name = agency_name or "Agency Request"
            
        elif requester_type == "STANDING_COMMITTEE" or requester_type == "NON_STANDING_COMMITTEE":
            sponsor_type = "Committee"
            sponsor_party = "Committee"
            committee_name = "Committee Request"
            sponsor_name = committee_name
        else:
            # It's a legislator, load the legislators lookup
            legislators_lookup_file = os.path.join(script_dir, "../interface/requester-lookup/legislators-lookup.json")
            if os.path.exists(legislators_lookup_file):
                with open(legislators_lookup_file, 'r') as f:
                    legislators_lookup = json.load(f)
                if str(sponsor_id) in legislators_lookup:
                    sponsor_name = legislators_lookup[str(sponsor_id)].get("legislatorName", "Unknown")
                    
            # Try to determine party
            # First try to load the legislators data for party information
            legislators_file = os.path.join(script_dir, "../interface/downloads/legislators/legislators.json")
            if os.path.exists(legislators_file):
                with open(legislators_file, 'r') as f:
                    try:
                        legislators_data = json.load(f)
                        # Find the legislator by ID
                        for legislator in legislators_data:
                            if legislator.get("id") == sponsor_id:
                                political_party = legislator.get("politicalParty", {})
                                if political_party:
                                    sponsor_party = political_party.get("name", "Unknown")
                                break
                    except json.JSONDecodeError:
                        pass
    
    return sponsor_name.strip(), sponsor_party, sponsor_type


def safe_get_nested(data, keys, default=""):
    """Safely get nested values from dictionaries"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current or default


def format_date(date_str):
    """Format date string for better readability"""
    try:
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
        return date_obj.strftime("%B %d, %Y")
    except:
        return date_str


def get_full_month(month_num):
    """Get full month name from month number"""
    month_mapping = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December"
    }
    return month_mapping.get(month_num, f"Month {month_num}")


def group_by_month(bill_date_dict):
    """Groups bills by month based on their dates."""
    month_mapping = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December"
    }
    month_counts = defaultdict(int)
    for _, date in bill_date_dict.items():
        try:
            month = date.split('/')[0]
            month_counts[month_mapping[month]] += 1
        except (IndexError, KeyError):
            print(f"Warning: Could not process date '{date}'")
    return month_counts


def add_manual_entries(house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed):
    """Add manually identified blast motions that might have been missed by the automated process"""
    # House failed blast motions with dates
    house_manual_failed = {
        "HB552": "03/03/2025",  # FAILED - HOUSE (03/03)
        "HB640": "03/05/2025"   # FAILED - HOUSE (03/05)
    }

    # Senate failed blast motions with dates
    senate_manual_failed = {
        "HB408": "04/23/2025",  # FAILED - SENATE (04/23)
        "HB569": "04/10/2025",  # FAILED - SENATE (04/10)
        "HB662": "04/10/2025",  # FAILED - SENATE (04/10)
        "SB8": "03/05/2025",    # FAILED - SENATE (03/05)
        "SB32": "04/02/2025",   # FAILED - SENATE (04/02)
        "SB130": "02/18/2025",  # FAILED - SENATE (02/18) (NO VOTES?)
        "SB179": "03/05/2025",  # FAILED - SENATE (03/05)
        "SB189": "03/25/2025",  # FAILED - SENATE (03/25)
        "SB225": "03/01/2025",  # FAILED - SENATE (03/01) (NO VOTES)
        "SB240": "03/01/2025",  # FAILED - SENATE (03/01) (NO VOTES)
        "SB250": "02/27/2025",  # FAILED - SENATE (02/27) (NO VOTES)
        "SB254": "03/05/2025",  # FAILED - SENATE (03/05)
        "SB323": "04/02/2025",  # FAILED - SENATE (04/02)
        "SB376": "03/01/2025",  # FAILED - SENATE (03/01)
        "SB415": "03/05/2025",  # FAILED - SENATE (03/05)
        "SB443": "03/01/2025",  # FAILED - SENATE (03/01)
        "SB526": "03/05/2025",  # FAILED - SENATE (03/05)
        "SB551": "04/04/2025",  # FAILED - SENATE (04/04)
    }

     # Add manual entries to the sets, ensuring they're formatted consistently
    for bill, date in house_manual_failed.items():
        bill = bill.replace(" ", "")  # Remove any spaces
        house_blasts_failed[bill] = date
        print(f"Added manual entry: {bill} on {date} (failed in House)")

    for bill, date in senate_manual_failed.items():
        bill = bill.replace(" ", "")  # Remove any spaces
        senate_blasts_failed[bill] = date
        print(f"Added manual entry: {bill} on {date} (failed in Senate)")

    return house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed


def process_blast_motions(session_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    actions_dir = os.path.join(script_dir, f'cleaned/actions-{session_id}')
    output_dir = os.path.join(script_dir, 'cleaned/blast-motions')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    house_blasts_passed = {}
    house_blasts_failed = {}
    senate_blasts_passed = {}
    senate_blasts_failed = {}

    if not os.path.exists(actions_dir):
        print(f"Warning: Actions directory {actions_dir} not found!")
        return

    print(f"Processing blast motions from {actions_dir}...")

    for file_name in os.listdir(actions_dir):
        if not file_name.endswith('-actions.json'):
            continue

        bill_actions = load_json_file(os.path.join(actions_dir, file_name))
        bill_id = file_name.replace('-actions.json', '')
        bill = bill_id.replace('-', '')

        for action in bill_actions:
            description = action.get('description', '').lower()
            if 'taken from committee' in description:
                possession = action.get('possession', '').lower()
                chamber = possession if possession in ['house', 'senate'] else None
                if not chamber:
                    continue

                action_date = action.get('date', '')
                vote = action.get('vote')
                yes_count = vote.get('count', {}).get('Y', 0) if vote else 0

                motion_passed = False
                if chamber == 'house' and yes_count >= 55:
                    motion_passed = True
                elif chamber == 'senate' and yes_count >= 26:
                    motion_passed = True

                if motion_passed:
                    if chamber == 'house':
                        house_blasts_passed[bill] = action_date
                    else:
                        senate_blasts_passed[bill] = action_date
                else:
                    if chamber == 'house':
                        house_blasts_failed[bill] = action_date
                    else:
                        senate_blasts_failed[bill] = action_date

    house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed = add_manual_entries(
        house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed
    )

    house_passed_by_month = group_by_month(house_blasts_passed)
    house_failed_by_month = group_by_month(house_blasts_failed)
    senate_passed_by_month = group_by_month(senate_blasts_passed)
    senate_failed_by_month = group_by_month(senate_blasts_failed)

    summary_data = {
        "house": {
            "passed": {"total": len(house_blasts_passed), "byMonth": house_passed_by_month},
            "failed": {"total": len(house_blasts_failed), "byMonth": house_failed_by_month},
            "total": len(house_blasts_passed) + len(house_blasts_failed)
        },
        "senate": {
            "passed": {"total": len(senate_blasts_passed), "byMonth": senate_passed_by_month},
            "failed": {"total": len(senate_blasts_failed), "byMonth": senate_failed_by_month},
            "total": len(senate_blasts_passed) + len(senate_blasts_failed)
        },
        "overall": {
            "passed": len(house_blasts_passed) + len(senate_blasts_passed),
            "failed": len(house_blasts_failed) + len(senate_blasts_failed),
            "total": len(house_blasts_passed) + len(house_blasts_failed) + len(senate_blasts_passed) + len(senate_blasts_failed)
        }
    }

    # Prepare enhanced CSV data with bill titles
    print("Getting bill titles...")
    csv_data = []
    
    # House passed
    for bill, date in house_blasts_passed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        sponsor_name, sponsor_party, sponsor_type = get_bill_sponsor_info(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name, 
            "status": "Passed",
            "chamber": "House",
            "result": "Successful Blast Motion",
            "sponsor": sponsor_name,
            "sponsor_party": sponsor_party,
            "sponsor_type": sponsor_type
        })
    
    # House failed
    for bill, date in house_blasts_failed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        sponsor_name, sponsor_party, sponsor_type = get_bill_sponsor_info(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Failed",
            "chamber": "House",
            "result": "Failed Blast Motion",
            "sponsor": sponsor_name,
            "sponsor_party": sponsor_party,
            "sponsor_type": sponsor_type
        })
    
    # Senate passed
    for bill, date in senate_blasts_passed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        sponsor_name, sponsor_party, sponsor_type = get_bill_sponsor_info(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Passed",
            "chamber": "Senate",
            "result": "Successful Blast Motion",
            "sponsor": sponsor_name,
            "sponsor_party": sponsor_party,
            "sponsor_type": sponsor_type
        })
    
    # Senate failed
    for bill, date in senate_blasts_failed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        sponsor_name, sponsor_party, sponsor_type = get_bill_sponsor_info(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Failed",
            "chamber": "Senate",
            "result": "Failed Blast Motion",
            "sponsor": sponsor_name,
            "sponsor_party": sponsor_party,
            "sponsor_type": sponsor_type
        })

    # Sort CSV data by date
    csv_data.sort(key=lambda x: (datetime.strptime(x['date'], '%m/%d/%Y'), x['bill']))

    # Create summary CSV data for quick overview
    summary_rows = []
    
    # House summary by month
    for month, count in house_passed_by_month.items():
        summary_rows.append({
            "chamber": "House",
            "month": month,
            "status": "Passed",
            "count": count
        })
    
    for month, count in house_failed_by_month.items():
        summary_rows.append({
            "chamber": "House",
            "month": month,
            "status": "Failed",
            "count": count
        })
    
    # Senate summary by month
    for month, count in senate_passed_by_month.items():
        summary_rows.append({
            "chamber": "Senate",
            "month": month,
            "status": "Passed",
            "count": count
        })
    
    for month, count in senate_failed_by_month.items():
        summary_rows.append({
            "chamber": "Senate",
            "month": month,
            "status": "Failed",
            "count": count
        })

    # Sort summary rows by month
    month_order = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    summary_rows.sort(key=lambda x: (x['chamber'], month_order[x['month']], x['status']))

    # Save output files
    summary_file = os.path.join(output_dir, 'passed-blast.json')
    detailed_csv_file = os.path.join(output_dir, 'blast-motions-detailed.csv')
    house_csv_file = os.path.join(output_dir, 'house-blast-motions-detailed.csv')
    senate_csv_file = os.path.join(output_dir, 'senate-blast-motions-detailed.csv')
    summary_csv_file = os.path.join(output_dir, 'blast-motions-summary.csv')

    # Filter data for house and senate
    house_csv_data = [row for row in csv_data if row['chamber'] == 'House']
    senate_csv_data = [row for row in csv_data if row['chamber'] == 'Senate']

    save_json_file(summary_data, summary_file)
    
    # Save the combined CSV
    save_csv_file(
    csv_data, 
    detailed_csv_file, 
    headers=["bill", "title", "date", "formatted_date", "month_number", 
            "month_name", "status", "chamber", "result", 
            "sponsor", "sponsor_party", "sponsor_type"]
    )
    
    # Save House-specific CSV
    save_csv_file(
        house_csv_data, 
        house_csv_file, 
        headers=["bill", "title", "date", "formatted_date", "month_number", 
            "month_name", "status", "chamber", "result", 
            "sponsor", "sponsor_party", "sponsor_type"]
    )
    
    # Save Senate-specific CSV
    save_csv_file(
        senate_csv_data, 
        senate_csv_file, 
        headers=["bill", "title", "date", "formatted_date", "month_number", 
            "month_name", "status", "chamber", "result", 
            "sponsor", "sponsor_party", "sponsor_type"]
    )
    
    # Save summary CSV
    save_csv_file(
        summary_rows,
        summary_csv_file,
        headers=["chamber", "month", "status", "count"]
    )

    print("\nSummary:")
    print(f"House blasts - {summary_data['house']['passed']['total']} passed, {summary_data['house']['failed']['total']} failed")
    print(f"Senate blasts - {summary_data['senate']['passed']['total']} passed, {summary_data['senate']['failed']['total']} failed")
    print(f"Output files saved to {output_dir}")
    print(f"CSV files created:")
    print(f"  - Combined: {detailed_csv_file}")
    print(f"  - House: {house_csv_file}")
    print(f"  - Senate: {senate_csv_file}")
    print(f"  - Summary: {summary_csv_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process blast motion data")
    parser.add_argument("session_id", type=str, help="Session ID for processing bill actions")
    args = parser.parse_args()

    process_blast_motions(args.session_id)