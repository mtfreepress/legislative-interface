import os
import json
import re
import datetime
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))

def analyze_transmittals(session_id, cutoff_date_str="03/06/2025"):
    # Convert cutoff date string to datetime object
    cutoff_date = datetime.datetime.strptime(cutoff_date_str, "%m/%d/%Y")
    
    house_bills_not_meeting_criteria = []
    senate_bills_not_meeting_criteria = []
    house_count = 0
    senate_count = 0
    
    bills_dir = os.path.join(os.path.dirname(script_dir), "downloads", f"raw-{session_id}-bills")
    
    # Ensure directory exists
    if not os.path.exists(bills_dir):
        print(f"Error: Directory {bills_dir} does not exist.")
        return
    
    # Regular expression to match bill files (HB-* or SB-*)
    bill_pattern = re.compile(r"(HB|SB)-\d+-raw-bill\.json")
    
    # Iterate through files in the directory
    for filename in os.listdir(bills_dir):
        match = bill_pattern.match(filename)
        if not match:
            continue
            
        bill_type = match.group(1)
        
        # Load bill data
        bill_path = os.path.join(bills_dir, filename)
        try:
            with open(bill_path, 'r') as f:
                bill_data = json.load(f)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
        
        # Check for deadlineCodeId = 3
        if bill_data.get("deadlineCodeId") != 3:
            continue
            
        # Get bill number and create bill identifier
        bill_number = bill_data.get("billNumber", "?")
        bill_identifier = f"{bill_type} {bill_number}"
        
        # Targeted debug print for HB 23
        if bill_identifier == "HB 23":
            print(f"Processing {bill_identifier}")
        
        # Check if bill has any of the specified actions before the cutoff date
        has_specific_action_before_cutoff = check_for_specific_actions(bill_data, cutoff_date, bill_identifier)
        
        # If no specific action before cutoff, add to appropriate list
        if not has_specific_action_before_cutoff:
            if bill_type == "HB":
                house_bills_not_meeting_criteria.append(bill_identifier)
                house_count += 1
            elif bill_type == "SB":
                senate_bills_not_meeting_criteria.append(bill_identifier)
                senate_count += 1
        else:
            if bill_identifier == "HB 23":
                print(f"HB 23 was excluded correctly.")
    
    # Sort the lists for better readability
    house_bills_not_meeting_criteria.sort(key=natural_sort_key)
    senate_bills_not_meeting_criteria.sort(key=natural_sort_key)
    
    # Write results to files
    print("Writing results to files...")
    write_results("transmittal-house", house_bills_not_meeting_criteria)
    write_results("transmittal-senate", senate_bills_not_meeting_criteria)
    
    # Write counts
    total_count = house_count + senate_count
    with open(os.path.join(script_dir, "transmittal-counts"), 'w') as f:
        f.write(f"House: {house_count}\n")
        f.write(f"Senate: {senate_count}\n")
        f.write(f"Total: {total_count}\n")
    
    print(f"Analysis complete. Found {house_count} House bills and {senate_count} Senate bills missing specific actions.")

def check_for_specific_actions(bill_data, cutoff_date, bill_identifier):
    """Check if bill has any of the specified actions before cutoff date."""
    specific_actions = [
        'Tabled in Committee',
        'Taken from Table in Committee',
        'Committee Vote Failed; Remains in Committee',
        'Reconsidered Previous Action; Remains in Committee',
        'Committee Executive Action--Resolution Adopted',
        'Committee Executive Action--Resolution Adopted as Amended',
        'Committee Executive Action--Resolution Not Adopted',
        'Committee Executive Action--Resolution Not Adopted as Amended',
        'Committee Executive Action--Bill Passed',
        'Committee Executive Action--Bill Passed as Amended',
        'Committee Executive Action--Bill Not Passed',
        'Committee Executive Action--Bill Not Passed as Amended',
        'Committee Executive Action--Bill Concurred',
        'Committee Executive Action--Bill Concurred as Amended',
        'Committee Executive Action--Bill Not Concurred',
        'Taken from Committee; Placed on 2nd Reading',
        'Bill Not Heard at Sponsor\'s Request',
        'Bill Withdrawn per House Rule H30-50(3)(b)',
        'Bill Withdrawn',
        'Missed Deadline for General Bill Transmittal',
        'Missed Deadline for Revenue Bill Transmittal',
        'Missed Deadline for Appropriation Bill Transmittal',
        'Missed Deadline for Referendum Proposal Transmittal',
        'Missed Deadline for Revenue Estimating Resolution Transmittal'
    ]
    
    exclude_actions = [
        'Bill Not Heard at Sponsor\'s Request',
        'Bill Withdrawn per House Rule H30-50(3)(b)',
        'Bill Withdrawn'
    ]
    
    # Check in billStatuses for specific actions
    if "draft" in bill_data and "billStatuses" in bill_data["draft"]:
        for status in bill_data["draft"]["billStatuses"]:
            # Look for specific action status codes
            if "billStatusCode" in status and "name" in status["billStatusCode"]:
                status_name = status["billStatusCode"]["name"]
                
                # Remove leading "(H) " or "(S) " from status name
                status_name = re.sub(r"^\(H\) |\(S\) ", "", status_name)
                
                # Check if this is an exclude action status
                if status_name in exclude_actions:
                    return True
                
                # Check if this is a specific action status
                if status_name in specific_actions:
                    # Check the timestamp
                    if "timeStamp" in status:
                        try:
                            # Parse the timestamp
                            action_date_str = status["timeStamp"]
                            action_date = datetime.datetime.fromisoformat(action_date_str.replace('Z', '+00:00'))
                            
                            # Compare with cutoff date
                            if action_date < cutoff_date:
                                return True
                        except (ValueError, TypeError) as e:
                            print(f"Error parsing date {status.get('timeStamp')}: {e}")
                            continue
    
    # If we reach here, no specific action was found before cutoff
    return False

def write_results(filename, bill_list):
    """Write bill list to a file."""
    with open(os.path.join(script_dir, filename), 'w') as f:
        for bill in bill_list:
            f.write(f"{bill}\n")

def natural_sort_key(s):
    """Key function for natural sorting of bill identifiers."""
    # Extract bill type and number
    match = re.match(r"(HB|SB)\s+(\d+)", s)
    if match:
        bill_type, bill_num = match.groups()
        return (0 if bill_type == "HB" else 1, int(bill_num))
    return (2, 0)  # Default for unexpected format

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python calculate-transmittals.py <session_id>")
        sys.exit(1)
        
    session_id = sys.argv[1]
    analyze_transmittals(session_id)