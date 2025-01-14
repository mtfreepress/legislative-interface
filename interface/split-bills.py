import os
import sys
import json

def safe_get(data, keys, default=None):
    """
    Safely retrieve nested dictionary values.
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

def save_bills_by_session(legislative_session):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, f"downloads/raw-{legislative_session}-bills.json")
    output_dir = os.path.join(script_dir, f"downloads/raw-{legislative_session}-bills")

    os.makedirs(output_dir, exist_ok=True)

    try:
        # load json
        with open(input_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        bills = data.get("content", [])
        if not isinstance(bills, list):
            raise ValueError("'content' key is missing or not a list.")

        # save each bill in own file
        for bill in bills:
            draft = bill.get("draft", {})
            draft_number = draft.get("draftNumber", "undefined")
            bill_type = safe_get(bill, ["billType", "code"], "undefined")
            bill_number = safe_get(bill, ["billNumber"], "undefined")

            # skip bills without both a bill_type and bill_number
            if not bill_type or not bill_number:
                continue

            output_file = os.path.join(output_dir, f"{bill_type}-{bill_number}-raw-bill.json")
            with open(output_file, "w", encoding="utf-8") as outfile:
                json.dump(bill, outfile, indent=4, ensure_ascii=False)

        print(f"Bills have been successfully separated into: {output_dir}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from '{input_file}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <legislative_session>")
        sys.exit(1)

    legislative_session = sys.argv[1]
    save_bills_by_session(legislative_session)
