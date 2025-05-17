import os
import sys
import json
import glob
import csv
import re
from pathlib import Path


def calculate_sponsor_stats():
    # get the directory of this script so it can be invoked from anywhere
    script_dir = Path(__file__).resolve().parent

    # define paths relative to script location
    legislators_path = script_dir / \
        "../../interface/downloads/legislators/legislators.json"
    bills_pattern = script_dir / "../../interface/downloads/raw-2-bills/*-*-raw-bill.json"

    # output paths
    output_dir = script_dir / "sponsor-stats"
    output_dir.mkdir(exist_ok=True)

    # individual sponsor stats output paths
    json_output_path = output_dir / "sponsor_stats.json"
    csv_output_path = output_dir / "sponsor_stats.csv"

    # party summary output paths
    party_json_output_path = output_dir / "party_stats.json"
    party_csv_output_path = output_dir / "party_stats.csv"

    # average stats output paths
    percentage_json_path = output_dir / "percentage_stats.json"
    percentage_csv_path = output_dir / "percentage_stats.csv"
    count_json_path = output_dir / "count_stats.json"
    count_csv_path = output_dir / "count_stats.csv"

    # load legislators data for mapping sponsor IDs to names
    with open(legislators_path, "r") as f:
        legislators_data = json.load(f)

    # create legislator lookup by ID
    legislator_map = {legislator["id"]                      : legislator for legislator in legislators_data}

    # dictionary to store statistics for each sponsor
    sponsor_stats = {}

    # dictionaries for party-based aggregations
    party_stats = {
        "House Democrats": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0},
        "House Republicans": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0},
        "Senate Democrats": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0},
        "Senate Republicans": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0},
        "Democrats": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0},
        "Republicans": {"billsSponsored": 0, "billsPassed": 0, "billsFailed": 0, "passPercentage": 0}
    }

    # lists to collect pass percentages by group for averaging
    # also track member counts and bill counts for each group
    group_stats = {
        "all": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "republicans": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "democrats": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "house": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "senate": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "houseRepublicans": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "houseDemocrats": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "senateRepublicans": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0},
        "senateDemocrats": {"pass_rates": [], "members": set(), "billsSponsored": 0, "billsPassed": 0}
    }

    # process all raw bill files
    bill_files = glob.glob(str(bills_pattern))
    for bill_file in bill_files:
        try:
            with open(bill_file, "r") as f:
                bill_data = json.load(f)

            # get sponsor ID from the bill
            sponsor_id = bill_data.get("sponsorId")

            # skip if no sponsor or not a legislator-sponsored bill
            if not sponsor_id or sponsor_id not in legislator_map:
                continue

            # get sponsor information
            sponsor = legislator_map[sponsor_id]
            sponsor_name = f"{sponsor.get('firstName', '')} {sponsor.get('lastName', '')}".strip(
            )
            party = sponsor.get("politicalParty", {}).get("name", "Unknown")
            district = sponsor.get("district", {}).get("name", "Unknown")
            chamber = sponsor.get("chamber", "Unknown").upper()

            # initialize sponsor stats if not already in dictionary
            if sponsor_name not in sponsor_stats:
                sponsor_stats[sponsor_name] = {
                    "sponsorId": sponsor_id,
                    "sponsor": sponsor_name,
                    "party": party,
                    "chamber": chamber,
                    "district": district,
                    # track all legislation
                    "legislationSponsored": 0,
                    "legislationPassed": 0,
                    "legislationFailed": 0,
                    "legislationPassPercentage": 0,
                    # track only HB/SB
                    "billsSponsored": 0,
                    "billsPassed": 0,
                    "billsFailed": 0,
                    "billsPassPercentage": 0
                }
            # increment bills sponsored count
           # Get the bill type code (HB, SB, etc.)
            bill_type_code = bill_data.get("billType", {}).get("code", "")
            
            # Always increment legislation counts (all types)
            sponsor_stats[sponsor_name]["legislationSponsored"] += 1

            # Only increment bill counts for HB and SB
            is_actual_bill = bill_type_code in ["HB", "SB"]
            if is_actual_bill:
                sponsor_stats[sponsor_name]["billsSponsored"] += 1

            # check if bill passed or failed
            bill_passed = False
            transmitted_to_governor = False
            vetoed = False

            # navigate through the nested structure to get to bill statuses
            draft_data = bill_data.get("draft", {})
            bill_statuses = draft_data.get("billStatuses", [])

            for status in bill_statuses:
                status_code = status.get("billStatusCode", {})
                bill_progress = status_code.get(
                    "billProgressCategory", {}).get("description", "")
                status_name = status_code.get("name", "")

                # check if bill became law
                if "Became Law" in bill_progress or "Signed by Governor" in status_name or "Chapter Number Assigned" in status_name:
                    bill_passed = True
                    break
                elif "Transmitted to Governor" in status_name or "(H) Transmitted to Governor" in status_name or "(S) Transmitted to Governor" in status_name:
                    transmitted_to_governor = True
                elif "Vetoed by Governor" in status_name:
                    vetoed = True

            # bill is considered passed if it became law OR was transmitted to governor but not vetoed
            if bill_passed or (transmitted_to_governor and not vetoed):
                bill_passed = True

            # update passed or failed count for individual sponsor
            if bill_passed:
                sponsor_stats[sponsor_name]["legislationPassed"] += 1
                if is_actual_bill:
                    sponsor_stats[sponsor_name]["billsPassed"] += 1
            else:
                sponsor_stats[sponsor_name]["legislationFailed"] += 1
                if is_actual_bill:
                    sponsor_stats[sponsor_name]["billsFailed"] += 1

            # update party aggregation stats
            # first determine which party categories this bill belongs to
            categories = []

            if party == "Democrat":
                categories.append("Democrats")
                if chamber == "HOUSE":
                    categories.append("House Democrats")
                elif chamber == "SENATE":
                    categories.append("Senate Democrats")
            elif party == "Republican":
                categories.append("Republicans")
                if chamber == "HOUSE":
                    categories.append("House Republicans")
                elif chamber == "SENATE":
                    categories.append("Senate Republicans")

            # update the appropriate party categories
            for category in categories:
                party_stats[category]["billsSponsored"] += 1
                if bill_passed:
                    party_stats[category]["billsPassed"] += 1
                else:
                    party_stats[category]["billsFailed"] += 1

            # track which groups this bill belongs to for group stats
            # all bills go into "all" category
            group_stats["all"]["billsSponsored"] += 1
            group_stats["all"]["members"].add(sponsor_id)
            if bill_passed:
                group_stats["all"]["billsPassed"] += 1

            # update group stats based on party and chamber
            if party == "Republican":
                group_stats["republicans"]["billsSponsored"] += 1
                group_stats["republicans"]["members"].add(sponsor_id)
                if bill_passed:
                    group_stats["republicans"]["billsPassed"] += 1

                if chamber == "HOUSE":
                    group_stats["houseRepublicans"]["billsSponsored"] += 1
                    group_stats["houseRepublicans"]["members"].add(sponsor_id)
                    if bill_passed:
                        group_stats["houseRepublicans"]["billsPassed"] += 1
                elif chamber == "SENATE":
                    group_stats["senateRepublicans"]["billsSponsored"] += 1
                    group_stats["senateRepublicans"]["members"].add(sponsor_id)
                    if bill_passed:
                        group_stats["senateRepublicans"]["billsPassed"] += 1

            elif party == "Democrat":
                group_stats["democrats"]["billsSponsored"] += 1
                group_stats["democrats"]["members"].add(sponsor_id)
                if bill_passed:
                    group_stats["democrats"]["billsPassed"] += 1

                if chamber == "HOUSE":
                    group_stats["houseDemocrats"]["billsSponsored"] += 1
                    group_stats["houseDemocrats"]["members"].add(sponsor_id)
                    if bill_passed:
                        group_stats["houseDemocrats"]["billsPassed"] += 1
                elif chamber == "SENATE":
                    group_stats["senateDemocrats"]["billsSponsored"] += 1
                    group_stats["senateDemocrats"]["members"].add(sponsor_id)
                    if bill_passed:
                        group_stats["senateDemocrats"]["billsPassed"] += 1

            if chamber == "HOUSE":
                group_stats["house"]["billsSponsored"] += 1
                group_stats["house"]["members"].add(sponsor_id)
                if bill_passed:
                    group_stats["house"]["billsPassed"] += 1
            elif chamber == "SENATE":
                group_stats["senate"]["billsSponsored"] += 1
                group_stats["senate"]["members"].add(sponsor_id)
                if bill_passed:
                    group_stats["senate"]["billsPassed"] += 1

        except Exception as e:
            print(f"Error processing {bill_file}: {e}")

    # calculate pass percentage for each sponsor
    for sponsor_name, stats in sponsor_stats.items():
        # calculate bill pass percentage (HB/SB only)
        if stats["billsSponsored"] > 0:
            stats["billsPassPercentage"] = round(
                (stats["billsPassed"] / stats["billsSponsored"]) * 100, 2)
                
        # calculate all legislation pass percentage
        if stats["legislationSponsored"] > 0:
            stats["legislationPassPercentage"] = round(
                (stats["legislationPassed"] / stats["legislationSponsored"]) * 100, 2)

        # add this sponsor's bill pass rate to the appropriate groups for averaging
        if stats["billsSponsored"] > 0:
            pass_rate = stats["billsPassPercentage"]
            group_stats["all"]["pass_rates"].append(pass_rate)

            if stats["party"] == "Republican":
                group_stats["republicans"]["pass_rates"].append(pass_rate)
                if stats["chamber"] == "HOUSE":
                    group_stats["houseRepublicans"]["pass_rates"].append(
                        pass_rate)
                elif stats["chamber"] == "SENATE":
                    group_stats["senateRepublicans"]["pass_rates"].append(
                        pass_rate)

            elif stats["party"] == "Democrat":
                group_stats["democrats"]["pass_rates"].append(pass_rate)
                if stats["chamber"] == "HOUSE":
                    group_stats["houseDemocrats"]["pass_rates"].append(
                        pass_rate)
                elif stats["chamber"] == "SENATE":
                    group_stats["senateDemocrats"]["pass_rates"].append(
                        pass_rate)

            if stats["chamber"] == "HOUSE":
                group_stats["house"]["pass_rates"].append(pass_rate)
            elif stats["chamber"] == "SENATE":
                group_stats["senate"]["pass_rates"].append(pass_rate)

    # calculate pass percentage for party summaries
    for party_name, stats in party_stats.items():
        if stats["billsSponsored"] > 0:
            stats["passPercentage"] = round(
                (stats["billsPassed"] / stats["billsSponsored"]) * 100, 2)

    # calculate average pass percentages and compile the full stats
    average_stats = {}
    for group, data in group_stats.items():
        group_key = group.capitalize() if group != "all" else ""
        member_count = len(data["members"])
        bills_sponsored = data["billsSponsored"]
        bills_passed = data["billsPassed"]

        if data["pass_rates"]:
            avg_rate = sum(data["pass_rates"]) / len(data["pass_rates"])
            average_stats[f"averagePass{group_key}"] = round(avg_rate, 2)
        else:
            average_stats[f"averagePass{group_key}"] = 0

        # add member and bill counts
        average_stats[f"memberCount{group_key}"] = member_count
        average_stats[f"billsSponsored{group_key}"] = bills_sponsored
        average_stats[f"billsPassed{group_key}"] = bills_passed

        # calculate overall pass rate for the group (not average of individual rates)
        if bills_sponsored > 0:
            group_pass_rate = (bills_passed / bills_sponsored) * 100
            average_stats[f"overallPassRate{group_key}"] = round(
                group_pass_rate, 2)
        else:
            average_stats[f"overallPassRate{group_key}"] = 0

    # add missing legislators with no bills sponsored
    missing_legislators = [
        {
            "sponsorId": "missing-1", 
            "sponsor": "Sidney Fitzpatrick", 
            "party": "Democrat", 
            "chamber": "HOUSE", 
            "district": "HD 42",
            "billsSponsored": 0,
            "billsPassed": 0,
            "billsFailed": 0,
            "billsPassPercentage": 0,
            "legislationSponsored": 0,
            "legislationPassed": 0,
            "legislationFailed": 0,
            "legislationPassPercentage": 0
        },
        {
            "sponsorId": "missing-2", 
            "sponsor": "Mike Fox", 
            "party": "Democrat", 
            "chamber": "HOUSE", 
            "district": "HD 32",
            "billsSponsored": 0,
            "billsPassed": 0,
            "billsFailed": 0,
            "billsPassPercentage": 0,
            "legislationSponsored": 0,
            "legislationPassed": 0,
            "legislationFailed": 0,
            "legislationPassPercentage": 0
        },
        {
            "sponsorId": "missing-3", 
            "sponsor": "Denise Hayman", 
            "party": "Democrat", 
            "chamber": "SENATE", 
            "district": "SD 32",
            "billsSponsored": 0,
            "billsPassed": 0,
            "billsFailed": 0,
            "billsPassPercentage": 0,
            "legislationSponsored": 0,
            "legislationPassed": 0,
            "legislationFailed": 0,
            "legislationPassPercentage": 0
        },
        {
            "sponsorId": "missing-4", 
            "sponsor": "Jacinda Morigeau", 
            "party": "Democrat", 
            "chamber": "SENATE", 
            "district": "SD 46",
            "billsSponsored": 0,
            "billsPassed": 0,
            "billsFailed": 0,
            "billsPassPercentage": 0,
            "legislationSponsored": 0,
            "legislationPassed": 0,
            "legislationFailed": 0,
            "legislationPassPercentage": 0
        }
    ]
    
    # add them to the sponsor_stats dictionary
    for legislator in missing_legislators:
        sponsor_name = legislator["sponsor"]
        if sponsor_name not in sponsor_stats:
            sponsor_stats[sponsor_name] = legislator
            
            # update the appropriate group member counts
            group_stats["all"]["members"].add(legislator["sponsorId"])
            
            if legislator["party"] == "Democrat":
                group_stats["democrats"]["members"].add(legislator["sponsorId"])
                if legislator["chamber"] == "HOUSE":
                    group_stats["houseDemocrats"]["members"].add(legislator["sponsorId"])
                    group_stats["house"]["members"].add(legislator["sponsorId"])
                elif legislator["chamber"] == "SENATE":
                    group_stats["senateDemocrats"]["members"].add(legislator["sponsorId"])
                    group_stats["senate"]["members"].add(legislator["sponsorId"])
            elif legislator["party"] == "Republican":
                group_stats["republicans"]["members"].add(legislator["sponsorId"])
                if legislator["chamber"] == "HOUSE":
                    group_stats["houseRepublicans"]["members"].add(legislator["sponsorId"])
                    group_stats["house"]["members"].add(legislator["sponsorId"])
                elif legislator["chamber"] == "SENATE":
                    group_stats["senateRepublicans"]["members"].add(legislator["sponsorId"])
                    group_stats["senate"]["members"].add(legislator["sponsorId"])

    # sort the individual results by number of bills sponsored (descending)
    sorted_stats = sorted(sponsor_stats.values(),
                          key=lambda x: x["billsSponsored"], reverse=True)
    
    legislators_dir = output_dir / "legislators"
    legislators_dir.mkdir(exist_ok=True)
    
    # Create separate directories for CSV and JSON files
    legislators_json_dir = legislators_dir / "json"
    legislators_csv_dir = legislators_dir / "csv"
    legislators_json_dir.mkdir(exist_ok=True)
    legislators_csv_dir.mkdir(exist_ok=True)
    
    # Collect bill details for each legislator during processing
    legislator_bills = {}
    
    # Second pass through bill files to collect bill titles and details
    print(f"Collecting detailed bill information for individual legislator reports...")
    for bill_file in bill_files:
        try:
            with open(bill_file, "r") as f:
                bill_data = json.load(f)
                
            # get sponsor ID and basic bill info
            sponsor_id = bill_data.get("sponsorId")
            if not sponsor_id or sponsor_id not in legislator_map:
                continue
                
            # find sponsor name
            sponsor = legislator_map[sponsor_id]
            sponsor_name = f"{sponsor.get('firstName', '')} {sponsor.get('lastName', '')}".strip()
            
            # bill details
            bill_number = bill_data.get("billNumber", "Unknown")
            bill_type_obj = bill_data.get("billType", {})
            bill_type = bill_type_obj.get("description", "") 
            
            draft_data = bill_data.get("draft", {})
            bill_title = draft_data.get("shortTitle", "Untitled Bill")
            bill_statuses = draft_data.get("billStatuses", [])
            
            # check bill status
            bill_passed = False
            transmitted_to_governor = False
            vetoed = False
            
            for status in bill_statuses:
                status_code = status.get("billStatusCode", {})
                bill_progress = status_code.get("billProgressCategory", {}).get("description", "")
                status_name = status_code.get("name", "")
                
                # check bill passage
                if "Became Law" in bill_progress or "Signed by Governor" in status_name or "Chapter Number Assigned" in status_name:
                    bill_passed = True
                elif "Transmitted to Governor" in status_name or "(H) Transmitted to Governor" in status_name or "(S) Transmitted to Governor" in status_name:
                    transmitted_to_governor = True
                elif "Vetoed by Governor" in status_name:
                    vetoed = True
            
            # bill is considered passed if it became law OR was transmitted to governor but not vetoed
            if bill_passed or (transmitted_to_governor and not vetoed):
                bill_passed = True
            
            #  final status
            bill_status = "Passed" if bill_passed else "Failed"
            
            # Clean up title
            if bill_title:
                bill_title = bill_title.replace("\n", " ").replace("  ", " ").strip()
                if len(bill_title) > 300:
                    bill_title = bill_title[:297] + "..."
            
            # bill entry
            bill_type_code = bill_data.get("billType", {}).get("code", "")
            bill_type = bill_data.get("billType", {}).get("description", "") 
            
            # bill entry
            bill_entry = {
                "billNumber": bill_number,
                "billType": bill_type,
                "billTypeCode": bill_type_code,  # Add the code for filtering
                "title": bill_title,
                "status": bill_status
            }
            
            # add to legislator
            if sponsor_name not in legislator_bills:
                legislator_bills[sponsor_name] = []
            
            legislator_bills[sponsor_name].append(bill_entry)
            
        except Exception as e:
            print(f"Error collecting bill details from {bill_file}: {e}")
    
    # missing legislators
    for legislator in missing_legislators:
        sponsor_name = legislator["sponsor"]
        if sponsor_name not in legislator_bills:
            legislator_bills[sponsor_name] = []
    
    # individual files for each legislator
    for sponsor_name, bills in legislator_bills.items():
        # sanitized filename from the sponsor name
        safe_name = re.sub(r'[^\w\s-]', '', sponsor_name).lower().replace(' ', '-')
        
        # Get the sponsor stats
        sponsor_stats_entry = sponsor_stats.get(sponsor_name, {
            "sponsorId": "unknown",
            "sponsor": sponsor_name,
            "party": "Unknown", 
            "chamber": "Unknown",
            "district": "Unknown",
            "billsSponsored": len([bill for bill in bills if bill.get("billTypeCode") in ["HB", "SB"]]),
            "billsPassed": sum(1 for bill in bills if bill["status"] == "Passed" and bill.get("billTypeCode") in ["HB", "SB"]),
            "billsFailed": sum(1 for bill in bills if bill["status"] == "Failed" and bill.get("billTypeCode") in ["HB", "SB"]),
            "billsPassPercentage": 0,
            "legislationSponsored": len(bills),
            "legislationPassed": sum(1 for bill in bills if bill["status"] == "Passed"),
            "legislationFailed": sum(1 for bill in bills if bill["status"] == "Failed"),
            "legislationPassPercentage": 0
        })
        
        # pass percentage for HB/SB bills
        if sponsor_stats_entry["billsSponsored"] > 0:
            sponsor_stats_entry["billsPassPercentage"] = round(
                (sponsor_stats_entry["billsPassed"] / sponsor_stats_entry["billsSponsored"]) * 100, 2)
                
        # pass percentage for all legislation
        if sponsor_stats_entry["legislationSponsored"] > 0:
            sponsor_stats_entry["legislationPassPercentage"] = round(
                (sponsor_stats_entry["legislationPassed"] / sponsor_stats_entry["legislationSponsored"]) * 100, 2)
        
        # full legislator record
        legislator_record = {
            "sponsor": sponsor_name,
            "party": sponsor_stats_entry["party"],
            "chamber": sponsor_stats_entry["chamber"],
            "district": sponsor_stats_entry["district"],
            "summary": {
                "billsSponsored": sponsor_stats_entry["billsSponsored"],
                "billsPassed": sponsor_stats_entry["billsPassed"],
                "billsFailed": sponsor_stats_entry["billsFailed"],
                "billsPassPercentage": sponsor_stats_entry["billsPassPercentage"],
                "legislationSponsored": sponsor_stats_entry["legislationSponsored"],
                "legislationPassed": sponsor_stats_entry["legislationPassed"],
                "legislationFailed": sponsor_stats_entry["legislationFailed"],
                "legislationPassPercentage": sponsor_stats_entry["legislationPassPercentage"]
            },
            "bills": sorted(bills, key=lambda x: x["billNumber"])
        }
        
        # Save JSON file
        json_path = legislators_json_dir / f"{safe_name}.json"
        with open(json_path, "w") as f:
            json.dump(legislator_record, f, indent=2)
        
        # Save CSV file
        csv_path = legislators_csv_dir / f"{safe_name}.csv"
        with open(csv_path, "w", newline="") as f:
            # Create header row - removed subjects
            fieldnames = ["billNumber", "billType", "title", "status"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write bills
            for bill in sorted(bills, key=lambda x: x["billNumber"]):
                writer.writerow({
                    "billNumber": bill["billNumber"],
                    "billType": bill["billType"],
                    "title": bill["title"],
                    "status": bill["status"]
                })
    
    print(f"Created individual bill reports for {len(legislator_bills)} legislators in {legislators_dir}")

    # convert party stats dict to list for JSON output
    party_stats_list = [{"category": key, **value}
                        for key, value in party_stats.items()]

    # save individual sponsor stats to JSON
    with open(json_output_path, "w") as f:
        json.dump(sorted_stats, f, indent=2)

    # save individual sponsor stats to CSV
    with open(csv_output_path, "w", newline="") as f:
        fieldnames = ["sponsor", "party", "chamber", "district",
                      "billsSponsored", "billsPassed", "billsFailed", "billsPassPercentage",
                      "legislationSponsored", "legislationPassed", "legislationFailed", "legislationPassPercentage"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for stat in sorted_stats:
            # Create a new dict with just the fields we want
            row = {field: stat.get(field, 0) for field in fieldnames}
            writer.writerow(row)

    # save party aggregation stats to JSON
    with open(party_json_output_path, "w") as f:
        json.dump(party_stats_list, f, indent=2)

    # save party aggregation stats to CSV
    with open(party_csv_output_path, "w", newline="") as f:
        fieldnames = ["category", "billsSponsored",
                      "billsPassed", "billsFailed", "passPercentage"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for category, stats in party_stats.items():
            writer.writerow({
                "category": category,
                "billsSponsored": stats["billsSponsored"],
                "billsPassed": stats["billsPassed"],
                "billsFailed": stats["billsFailed"],
                "passPercentage": stats["passPercentage"]
            })

    percentage_stats = {}
    count_stats = {}

    for key, value in average_stats.items():
        # Only include genuine percentage/rate metrics in percentage_stats
        if key.startswith("average") or key.startswith("overallPassRate") or key.endswith("Percentage"):
            percentage_stats[key] = value
        # Move all "bills" count metrics to count_stats
        elif key.startswith("bills") or "Count" in key or "Total" in key:
            count_stats[key] = value
        # Add any other metrics to count_stats by default
        else:
            count_stats[key] = value

    # Save percentage stats to JSON
    with open(percentage_json_path, "w") as f:
        json.dump(percentage_stats, f, indent=2)

    # Save percentage stats to CSV
    with open(percentage_csv_path, "w", newline="") as f:
        fieldnames = ["metric", "value"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for metric, value in percentage_stats.items():
            writer.writerow({"metric": metric, "value": value})

    # Save count stats to JSON
    with open(count_json_path, "w") as f:
        json.dump(count_stats, f, indent=2)

    # Save count stats to CSV
    with open(count_csv_path, "w", newline="") as f:
        fieldnames = ["metric", "value"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for metric, value in count_stats.items():
            writer.writerow({"metric": metric, "value": value})

    print(
        f"Sponsor statistics saved to {json_output_path} and {csv_output_path}")
    print(
        f"Party statistics saved to {party_json_output_path} and {party_csv_output_path}")
    print(
        f"Percentage statistics saved to {percentage_json_path} and {percentage_csv_path}")
    print(f"Count statistics saved to {count_json_path} and {count_csv_path}")
    print(
        f"Processed {len(bill_files)} bill files for {len(sponsor_stats)} sponsors")


if __name__ == "__main__":
    calculate_sponsor_stats()