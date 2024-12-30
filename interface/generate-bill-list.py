import os
import json

# TODO maybe combine this with the process-bills

# Constants
# 2023
# session = 20231

# 2025
session = 2
json_file = f"../interface/downloads/raw-{session}-bills.json"

# Load JSON file
with open(json_file, "r") as f:
    json_data = json.load(f)
# 2023

# bills = json_data.get("bills", {}).get("content", [])

bills = json_data.get("content", [])
output = []

# Iterate through bills and extract `lc` and `key`
for bill in bills:
    draft = bill.get("id", {})
    draft_number = draft.get("billDraftNumber", "undefined")
    bill_type = (bill.get("billType") or "").upper()
    bill_number = bill.get("billNumber", "undefined")

    # Skip if `billType` and `billNumber` are missing
    if not bill_type and not bill_number:
        continue

    # Determine the bill key
    # bill_key = f"{bill_type} {bill_number}" if bill_type and bill_number else draft_number

    # Add to the output list
    output.append({"lc": draft_number, 
                   "billType": bill_type,
                   "billNumber": bill_number
                   })

# Save output to a file (optional)
output_file = f"fast-list-bills-{session}.json"
with open(output_file, "w") as f:
    json.dump(output, f, indent=2)