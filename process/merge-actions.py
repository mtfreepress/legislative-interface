import os
import json
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_BILLS_PATH_TEMPLATE = os.path.join(BASE_DIR, '../interface/list-bills-{}.json')
MATCHED_ACTIONS_DIR_TEMPLATE = os.path.join(BASE_DIR, '../interface/downloads/matched-{}-votes')
OUTPUT_DIR_TEMPLATE = os.path.join(BASE_DIR, 'cleaned/merged-actions-{}')

def parse_arguments():
    parser = argparse.ArgumentParser(description="Merge and chunk bill actions.")
    parser.add_argument('session_id', type=str, help="Legislative session ID")
    return parser.parse_args()

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def write_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def main():
    args = parse_arguments()
    session_id = args.session_id

    list_bills_path = LIST_BILLS_PATH_TEMPLATE.format(session_id)
    matched_actions_dir = MATCHED_ACTIONS_DIR_TEMPLATE.format(session_id)
    output_dir = OUTPUT_DIR_TEMPLATE.format(session_id)

    list_bills = load_json(list_bills_path)
    actions_output = []

    for bill in list_bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']
        bill_name = f"{bill_type}-{bill_number}"
        matched_actions_file = os.path.join(matched_actions_dir, f"{bill_name}-matched-actions.json")

        if os.path.exists(matched_actions_file):
            matched_actions = load_json(matched_actions_file)
            actions_output.append({
                "bill": f"{bill_type} {bill_number}",
                "actions": matched_actions
            })

    os.makedirs(output_dir, exist_ok=True)

    chunk_size = 200
    index = 1
    for start in range(0, len(actions_output), chunk_size):
        chunk = actions_output[start:start + chunk_size]
        output_file_path = os.path.join(output_dir, f"bill-actions-{index}.json")
        write_json(output_file_path, chunk)
        index += 1

if __name__ == "__main__":
    main()