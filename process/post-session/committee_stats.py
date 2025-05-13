import os
import json
import csv
from pathlib import Path
from collections import defaultdict

def analyze_committee_bills(session_id):
    """
    Analyze bills by first committee they were sent to, tracking pass/fail rates.
    """
    # Get the directory of this script so it can be invoked from anywhere
    script_dir = Path(__file__).resolve().parent
    
    # Define paths relative to script location
    actions_dir = script_dir / f"../cleaned/actions-{session_id}"
    output_dir = script_dir / "committee-stats"
    output_dir.mkdir(exist_ok=True)
    
    # Output paths
    json_output_path = output_dir / "committee_stats.json"
    csv_output_path = output_dir / "committee_stats.csv"
    
    # Dictionary to store committee statistics
    committee_stats = defaultdict(lambda: {
        "billTotal": 0,
        "passedTotal": 0,
        "failedTotal": 0,
        "billList": [],
        "passedBills": [],
        "failedBills": []
    })
    
    # Process all action files
    action_files = list(actions_dir.glob("*-actions.json"))
    print(f"Found {len(action_files)} bill action files to process.")
    
    for action_file in action_files:
        try:
            with open(action_file, "r") as f:
                actions = json.load(f)
            
            # Get bill identifier from filename (e.g., "HB-1-actions.json" -> "HB 1")
            bill_id = action_file.stem.replace("-actions", "").replace("-", " ")
            
                        # Find the first committee the bill was referred to
            first_committee = None
            bill_passed = False
            transmitted_to_governor = False
            vetoed = False
            
            for action in actions:
                # Find first committee referral
                if action.get("key") == "Referred to Committee" and action.get("committee") != "undefined":
                    first_committee = action.get("committee")
                    break
            
            # If no committee found, skip this bill
            if not first_committee:
                continue
                
            # Check if bill ultimately passed
            for action in actions:
                description = action.get("description", "")
                key = action.get("key", "")
                
                if (
                    "Became Law" in description or 
                    "Signed by Governor" in description or 
                    "Chapter Number Assigned" in key or 
                    "Chapter Number Assigned" in description
                ):
                    bill_passed = True
                    break
                elif "Transmitted to Governor" in description or "(H) Transmitted to Governor" in description or "(S) Transmitted to Governor" in description:
                    transmitted_to_governor = True
                elif "Vetoed by Governor" in description:
                    vetoed = True
            
            # A bill is considered passed if it became law OR was transmitted to governor but not vetoed
            if bill_passed or (transmitted_to_governor and not vetoed):
                bill_passed = True
            
            # Update committee statistics
            committee_stats[first_committee]["billTotal"] += 1
            committee_stats[first_committee]["billList"].append(bill_id)
            
            if bill_passed:
                committee_stats[first_committee]["passedTotal"] += 1
                committee_stats[first_committee]["passedBills"].append(bill_id)
            else:
                committee_stats[first_committee]["failedTotal"] += 1
                committee_stats[first_committee]["failedBills"].append(bill_id)
                
        except Exception as e:
            print(f"Error processing {action_file}: {e}")
    
    # Calculate percentages and format output
    results = []
    for committee, stats in committee_stats.items():
        if stats["billTotal"] == 0:
            continue
            
        # Join bill lists for output
        stats["billList"] = ", ".join(stats["billList"])
        stats["passedBills"] = ", ".join(stats["passedBills"])
        stats["failedBills"] = ", ".join(stats["failedBills"])
        
        # Calculate pass percentage
        pass_percentage = (stats["passedTotal"] / stats["billTotal"]) * 100 if stats["billTotal"] > 0 else 0
        
        # Add to results with committee name
        results.append({
            "committee": committee,
            "billTotal": stats["billTotal"],
            "passedTotal": stats["passedTotal"],
            "failedTotal": stats["failedTotal"],
            "passPercentage": round(pass_percentage, 2),
            "billList": stats["billList"],
            "passedBills": stats["passedBills"],
            "failedBills": stats["failedBills"]
        })
    
    # Sort by bill total (most bills first)
    results = sorted(results, key=lambda x: x["billTotal"], reverse=True)
    
    # Save to JSON
    with open(json_output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Save to CSV
    with open(csv_output_path, "w", newline="") as f:
        fieldnames = ["committee", "billTotal", "passedTotal", "failedTotal", 
                     "passPercentage", "billList", "passedBills", "failedBills"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    
    committee_output_dir = output_dir / "by-committee"
    committee_output_dir.mkdir(exist_ok=True)

    json_dir = committee_output_dir / "json"
    json_dir.mkdir(exist_ok=True)

    csv_dir = committee_output_dir / "csv"
    csv_dir.mkdir(exist_ok=True)

    bills_csv_dir = committee_output_dir / "bills-csv"
    bills_csv_dir.mkdir(exist_ok=True)

    print(f"Creating individual committee files for {len(results)} committees...")

    # Process each committee and create separate files
    for committee_data in results:
        committee = committee_data["committee"]
        
        # Format committee name for filename (replace spaces, slashes, etc. with underscores)
        safe_committee_name = committee.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        safe_committee_name = ''.join(c if c.isalnum() or c == '_' else '' for c in safe_committee_name)
        
        # Skip empty committee names
        if not safe_committee_name:
            print(f"Skipping committee with empty name: {committee}")
            continue
            
        try:
            # Save to individual JSON file
            json_path = json_dir / f"{safe_committee_name}.json"
            with open(json_path, "w") as f:
                json.dump(committee_data, f, indent=2)
            
            # Save to individual CSV file (key-value format)
            csv_path = csv_dir / f"{safe_committee_name}.csv"
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                # Write headers and data as rows
                writer.writerow(["Metric", "Value"])
                for key, value in committee_data.items():
                    writer.writerow([key, value])
                
            # Create a bills-only CSV which is easier to work with in Excel
            bills_csv_path = bills_csv_dir / f"{safe_committee_name}_bills.csv"
            with open(bills_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Bill", "Status"])
                
                # Split the comma-separated lists back into individual bills
                if committee_data["passedBills"]:
                    passed_bills = committee_data["passedBills"].split(", ") if isinstance(committee_data["passedBills"], str) else committee_data["passedBills"]
                    for bill in passed_bills:
                        writer.writerow([bill, "Passed"])
                
                if committee_data["failedBills"]:
                    failed_bills = committee_data["failedBills"].split(", ") if isinstance(committee_data["failedBills"], str) else committee_data["failedBills"]
                    for bill in failed_bills:
                        writer.writerow([bill, "Failed"])
        
        except Exception as e:
            print(f"Error creating files for committee '{committee}': {e}")

    

    print(f"Committee statistics saved to {json_output_path} and {csv_output_path}")
    print(f"Individual committee JSON files saved in {json_dir}")
    print(f"Individual committee CSV files saved in {csv_dir}")
    print(f"Individual committee bill lists saved in {bills_csv_dir}")
    print(f"Processed {len(action_files)} bill files for {len(results)} committees")

if __name__ == "__main__":
    import sys
    session_id = sys.argv[1] if len(sys.argv) > 1 else "2"
    analyze_committee_bills(session_id)