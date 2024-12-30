import json

# constants
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

# iterate through bills and extract `lc` and `key`
for bill in bills:
    draft = bill.get("draft", {})
    draft_number = draft.get("draftNumber", "undefined")
    bill_type_data = bill.get("billType", {})
    bill_type = (bill_type_data.get("code", "") if bill_type_data else "").upper()
    
    bill_number = bill.get("billNumber", "undefined")

    # skip if `billType` and `billNumber` are missing
    if not bill_type and not bill_number:
        continue

    # add to output list
    output.append({"lc": draft_number, 
                   "billType": bill_type,
                   "billNumber": bill_number
                   })

output_file = f"list-bills-{session}.json"
with open(output_file, "w") as f:
    json.dump(output, f, indent=2)