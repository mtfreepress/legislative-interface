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
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name, 
            "status": "Passed",
            "chamber": "House",
            "result": "Successful Blast Motion"
        })
    
    # House failed
    for bill, date in house_blasts_failed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Failed",
            "chamber": "House",
            "result": "Failed Blast Motion"
        })
    
    # Senate passed
    for bill, date in senate_blasts_passed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Passed",
            "chamber": "Senate",
            "result": "Successful Blast Motion"
        })
    
    # Senate failed
    for bill, date in senate_blasts_failed.items():
        month_num = date.split('/')[0]
        month_name = get_full_month(month_num)
        title = get_bill_title(bill, session_id)
        csv_data.append({
            "bill": bill,
            "title": title,
            "date": date,
            "formatted_date": format_date(date),
            "month_number": month_num,
            "month_name": month_name,
            "status": "Failed",
            "chamber": "Senate",
            "result": "Failed Blast Motion"
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
                "month_name", "status", "chamber", "result"]
    )
    
    # Save House-specific CSV
    save_csv_file(
        house_csv_data, 
        house_csv_file, 
        headers=["bill", "title", "date", "formatted_date", "month_number", 
                "month_name", "status", "chamber", "result"]
    )
    
    # Save Senate-specific CSV
    save_csv_file(
        senate_csv_data, 
        senate_csv_file, 
        headers=["bill", "title", "date", "formatted_date", "month_number", 
                "month_name", "status", "chamber", "result"]
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

# import os
# import json
# import argparse
# from collections import defaultdict


# def load_json_file(file_path):
#     try:
#         with open(file_path, 'r') as file:
#             return json.load(file)
#     except Exception as e:
#         print(f"Error loading {file_path}: {e}")
#         return []


# def save_json_file(data, file_path):
#     with open(file_path, 'w') as file:
#         json.dump(data, file, indent=2)

# def group_by_month(bill_date_dict):
#     """
#     Groups bills by month based on their dates.
#     Returns a dictionary with month names as keys and counts as values.
#     """
#     # Month mapping with both number and name
#     month_mapping = {
#         "01": "January",
#         "02": "February",
#         "03": "March",
#         "04": "April",
#         "05": "May",
#         "06": "June",
#         "07": "July",
#         "08": "August",
#         "09": "September",
#         "10": "October",
#         "11": "November",
#         "12": "December"
#     }
    
#     # Initialize counts dictionary
#     month_counts = {month_num: 0 for month_num in month_mapping.keys()}
    
#     for bill, date in bill_date_dict.items():
#         try:
#             # Extract month from date string (assuming MM/DD/YYYY format)
#             month = date.split('/')[0]
#             month_counts[month] += 1
#         except (IndexError, KeyError) as e:
#             print(f"Warning: Could not process date '{date}' for bill {bill}: {e}")
    
#     # Create a formatted output with both number and name, but only for months with counts > 0
#     formatted_counts = {}
#     for month_num, count in month_counts.items():
#         if count > 0:
#             month_name = month_mapping.get(month_num, "Unknown")
#             formatted_counts[f"{month_num} - {month_name}"] = count
    
#     return formatted_counts


# def add_manual_entries(house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed):
#     """Add manually identified blast motions that might have been missed by the automated process"""

#     # House failed blast motions with dates
#     house_manual_failed = {
#         "HB552": "03/03/2025",  # FAILED - HOUSE (03/03)
#         "HB640": "03/05/2025"   # FAILED - HOUSE (03/05)
#     }

#     # Senate failed blast motions with dates
#     senate_manual_failed = {
#         "HB408": "04/23/2025",  # FAILED - SENATE (04/23)
#         "HB569": "04/10/2025",  # FAILED - SENATE (04/10)
#         "HB662": "04/10/2025",  # FAILED - SENATE (04/10)
#         "SB8": "03/05/2025",    # FAILED - SENATE (03/05)
#         "SB32": "04/02/2025",   # FAILED - SENATE (04/02)
#         "SB130": "02/18/2025",  # FAILED - SENATE (02/18) (NO VOTES?)
#         "SB179": "03/05/2025",  # FAILED - SENATE (03/05)
#         "SB189": "03/25/2025",  # FAILED - SENATE (03/25)
#         "SB225": "03/01/2025",  # FAILED - SENATE (03/01) (NO VOTES)
#         "SB240": "03/01/2025",  # FAILED - SENATE (03/01) (NO VOTES)
#         "SB250": "02/27/2025",  # FAILED - SENATE (02/27) (NO VOTES)
#         "SB254": "03/05/2025",  # FAILED - SENATE (03/05)
#         "SB323": "04/02/2025",  # FAILED - SENATE (04/02)
#         "SB376": "03/01/2025",  # FAILED - SENATE (03/01)
#         "SB415": "03/05/2025",  # FAILED - SENATE (03/05)
#         "SB443": "03/01/2025",  # FAILED - SENATE (03/01)
#         "SB526": "03/05/2025",  # FAILED - SENATE (03/05)
#         "SB551": "04/04/2025",  # FAILED - SENATE (04/04)
#     }

#     # Add manual entries to the sets, ensuring they're formatted consistently
#     for bill, date in house_manual_failed.items():
#         bill = bill.replace(" ", "")  # Remove any spaces
#         house_blasts_failed[bill] = date
#         print(f"Added manual entry: {bill} on {date} (failed in House)")

#     for bill, date in senate_manual_failed.items():
#         bill = bill.replace(" ", "")  # Remove any spaces
#         senate_blasts_failed[bill] = date
#         print(f"Added manual entry: {bill} on {date} (failed in Senate)")

#     # Check for and fix any duplicates (bills that appear in both passed and failed lists)
#     duplicates_house = set(house_blasts_passed.keys()).intersection(
#         set(house_blasts_failed.keys()))
#     duplicates_senate = set(senate_blasts_passed.keys()).intersection(
#         set(senate_blasts_failed.keys()))

#     if duplicates_house:
#         print(
#             f"Warning: Found bills in both passed and failed House lists: {duplicates_house}")
#         print("Using manual entries as the source of truth...")
#         for bill in duplicates_house:
#             house_blasts_passed.pop(bill, None)
#             print(f"  Removed {bill} from passed list, keeping in failed list")

#     if duplicates_senate:
#         print(
#             f"Warning: Found bills in both passed and failed Senate lists: {duplicates_senate}")
#         print("Using manual entries as the source of truth...")
#         for bill in duplicates_senate:
#             senate_blasts_passed.pop(bill, None)
#             print(f"  Removed {bill} from passed list, keeping in failed list")

#     return house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed


# def process_blast_motions(session_id):
#     # Define paths — relative to script to avoid issues when invoking from anywhere
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     actions_dir = os.path.join(script_dir, f'cleaned/actions-{session_id}')
#     output_dir = os.path.join(script_dir, 'cleaned/blast-motions')

#     # Create output directory if it doesn't exist
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir, exist_ok=True)

#     # Initialize tracking structures as dictionaries to store dates
#     house_blasts_passed = {}  # {bill: date}
#     house_blasts_failed = {}
#     senate_blasts_passed = {}
#     senate_blasts_failed = {}

#     # Process all action files
#     if not os.path.exists(actions_dir):
#         print(f"Warning: Actions directory {actions_dir} not found!")
#         return

#     print(f"Processing blast motions from {actions_dir}...")

#     for file_name in os.listdir(actions_dir):
#         if not file_name.endswith('-actions.json'):
#             continue

#         bill_actions = load_json_file(os.path.join(actions_dir, file_name))
#         bill_id = file_name.replace('-actions.json', '')
#         bill = bill_id.replace('-', '')  # Format like "HB170"

#         # Process each action for this bill
#         for i, action in enumerate(bill_actions):
#             description = action.get('description', '').lower()

#             # Check if this is a blast motion
#             if 'taken from committee' in description:
#                 # Get the chamber from possession field
#                 possession = action.get('possession', '').lower()
#                 chamber = possession if possession in [
#                     'house', 'senate'] else None

#                 if not chamber:
#                     print(
#                         f"Warning: Unable to determine chamber for blast motion in {bill}")
#                     continue

#                 # Get date from vote if available, otherwise from action
#                 action_date = action.get('date', '')
#                 if action.get('vote') and action.get('vote').get('date'):
#                     action_date = action.get('vote').get('date')

#                 print(
#                     f"Found blast motion in {bill} ({chamber}) on {action_date}: {action.get('description')}")

#                 # Check if the blast motion succeeded
#                 vote = action.get('vote')
#                 if vote and isinstance(vote, dict):
#                     # Get the vote counts
#                     yes_count = vote.get('count', {}).get('Y', 0)

#                     # Determine if it passed based on chamber-specific thresholds
#                     motion_passed = False
#                     if chamber == 'house' and yes_count >= 55:  # House needs 55+ votes
#                         motion_passed = True
#                     elif chamber == 'senate' and yes_count >= 26:  # Senate needs 26+ votes
#                         motion_passed = True

#                     # Debug output
#                     if chamber == 'house':
#                         threshold = 55
#                     else:
#                         threshold = 26

#                     print(
#                         f"  Vote count: {yes_count}/{threshold} required in the {chamber}")

#                     if motion_passed:
#                         print(f"  Blast motion PASSED for {bill}")
#                         if chamber == 'house':
#                             house_blasts_passed[bill] = action_date
#                         else:
#                             senate_blasts_passed[bill] = action_date
#                     else:
#                         print(f"  Blast motion FAILED for {bill}")
#                         if chamber == 'house':
#                             house_blasts_failed[bill] = action_date
#                         else:
#                             senate_blasts_failed[bill] = action_date
#                 else:
#                     print(
#                         f"  No vote data for blast motion in {bill}. Examining next action...")

#                     # Check if the next action indicates success (like "2nd Reading")
#                     # This is a fallback if vote data isn't available
#                     blast_index = bill_actions.index(action)
#                     if blast_index + 1 < len(bill_actions):
#                         next_action = bill_actions[blast_index + 1]
#                         next_desc = next_action.get('description', '').lower()

#                         if '2nd reading' in next_desc or 'placed on 2nd reading' in next_desc:
#                             print(
#                                 f"  Based on next action, blast motion PASSED for {bill}")
#                             if chamber == 'house':
#                                 house_blasts_passed[bill] = action_date
#                             else:
#                                 senate_blasts_passed[bill] = action_date
#                         else:
#                             print(
#                                 f"  Based on next action, assuming blast motion FAILED for {bill}")
#                             if chamber == 'house':
#                                 house_blasts_failed[bill] = action_date
#                             else:
#                                 senate_blasts_failed[bill] = action_date

#     # Clean bill numbers (remove spaces) and keep the dates
#     house_blasts_passed = {bill.replace(
#         " ", ""): date for bill, date in house_blasts_passed.items()}
#     house_blasts_failed = {bill.replace(
#         " ", ""): date for bill, date in house_blasts_failed.items()}
#     senate_blasts_passed = {bill.replace(
#         " ", ""): date for bill, date in senate_blasts_passed.items()}
#     senate_blasts_failed = {bill.replace(
#         " ", ""): date for bill, date in senate_blasts_failed.items()}

#     # After cleaning, add manual entries
#     house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed = add_manual_entries(
#         house_blasts_passed, house_blasts_failed, senate_blasts_passed, senate_blasts_failed
#     )

#     house_passed_by_month = group_by_month(house_blasts_passed)
#     house_failed_by_month = group_by_month(house_blasts_failed)
#     senate_passed_by_month = group_by_month(senate_blasts_passed)
#     senate_failed_by_month = group_by_month(senate_blasts_failed)
    
#     # Prepare output data with monthly breakdown
#     summary_data = {
#         "house": {
#             "passed": {
#                 "total": len(house_blasts_passed),
#                 "byMonth": house_passed_by_month
#             },
#             "failed": {
#                 "total": len(house_blasts_failed),
#                 "byMonth": house_failed_by_month
#             },
#             "total": len(house_blasts_passed) + len(house_blasts_failed)
#         },
#         "senate": {
#             "passed": {
#                 "total": len(senate_blasts_passed),
#                 "byMonth": senate_passed_by_month
#             },
#             "failed": {
#                 "total": len(senate_blasts_failed),
#                 "byMonth": senate_failed_by_month
#             },
#             "total": len(senate_blasts_passed) + len(senate_blasts_failed)
#         }
#     }

#     # Create formatted output with sorted dates
#     house_passed_sorted = sorted(
#         house_blasts_passed.items(), key=lambda x: x[1])
#     house_failed_sorted = sorted(
#         house_blasts_failed.items(), key=lambda x: x[1])
#     senate_passed_sorted = sorted(
#         senate_blasts_passed.items(), key=lambda x: x[1])
#     senate_failed_sorted = sorted(
#         senate_blasts_failed.items(), key=lambda x: x[1])

#     house_blasts_data = {
#         "passed": [{"bill": bill, "date": date} for bill, date in house_passed_sorted],
#         "failed": [{"bill": bill, "date": date} for bill, date in house_failed_sorted]
#     }

#     senate_blasts_data = {
#         "passed": [{"bill": bill, "date": date} for bill, date in senate_passed_sorted],
#         "failed": [{"bill": bill, "date": date} for bill, date in senate_failed_sorted]
#     }

#     # Save output files
#     summary_file = os.path.join(output_dir, 'passed-blast.json')
#     house_file = os.path.join(output_dir, 'houseBlasts.json')
#     senate_file = os.path.join(output_dir, 'senateBlasts.json')

#     save_json_file(summary_data, summary_file)
#     save_json_file(house_blasts_data, house_file)
#     save_json_file(senate_blasts_data, senate_file)

#     print("\nSummary:")
#     print(
#         f"House blasts - {summary_data['house']['passed']} passed, {summary_data['house']['failed']} failed")
#     print(
#         f"Senate blasts - {summary_data['senate']['passed']} passed, {summary_data['senate']['failed']} failed")
#     print(f"Output files saved to {output_dir}")
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Process blast motion data")
#     parser.add_argument("session_id", type=str,
#                         help="Session ID for processing bill actions")
#     args = parser.parse_args()

#     process_blast_motions(args.session_id)
