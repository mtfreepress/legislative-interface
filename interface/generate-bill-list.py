import json
import os
import sys

# Load JSON file


def load_bills(session_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(
        script_dir, f"../interface/downloads/raw-{session_id}-bills.json")
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON in file: {json_file}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python list-bills.py <sessionId>")
        sys.exit(1)

    # Get session_id from command-line arguments
    session_id = sys.argv[1]

    # Load bills data
    json_data = load_bills(session_id)

    bills = json_data.get("content", [])
    output = []

    # Iterate through bills and extract `lc` and `key`
    for bill in bills:
        draft = bill.get("draft", {})
        id = bill.get("id", "undefined")
        draft_number = draft.get("draftNumber", "undefined")
        bill_type_data = bill.get("billType", {})
        bill_type = (bill_type_data.get("code", "")
                     if bill_type_data else "").upper()

        bill_number = bill.get("billNumber", "undefined")

        # Skip if `billType` and `billNumber` are missing
        if not bill_type and not bill_number:
            continue

        # Add to output list
        output.append({"lc": draft_number,
                       "id": id,
                       "billType": bill_type,
                       "billNumber": bill_number
                       })

    # Save extracted data to output file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f"list-bills-{session_id}.json")
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Extracted bill list saved to '{output_file}'.")
