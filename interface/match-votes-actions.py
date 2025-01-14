import json
import os
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

votes_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-votes")
bills_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-bills")
list_bills_file = os.path.join(BASE_DIR, "../list-bills-2.json")

# parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Match votes and bill statuses.")
    parser.add_argument("session_id", type=str, help="Legislative session ID")
    return parser.parse_args()

# load list of bills
with open(list_bills_file, "r") as f:
    list_bills = json.load(f)

def main():
    args = parse_arguments()
    session_id = args.session_id  # get session_id from arguments

    # testing purposes - process only HB 1
    # bill_type = "HB"
    # bill_number = 1

    # iterate through bills in the list
    for bill in list_bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        # build paths to vote and bill data files
        vote_file_path = os.path.join(votes_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-votes.json")
        bill_file_path = os.path.join(bills_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-bill.json")

        # load vote data
        with open(vote_file_path, "r") as f:
            votes_data = json.load(f)

        # load bill data
        with open(bill_file_path, "r") as f:
            bill_data = json.load(f)

        # match votes and bill statuses
        for item in votes_data:
            bill_status_id = item.get('billStatus', {}).get('id') or item.get('billStatusId')  # handle structural difference
            if bill_status_id:
                for bill_status in bill_data.get('draft', {}).get('billStatuses', []):
                    if bill_status['id'] == bill_status_id:
                        # print matched info
                        print(f"Matched Item ID: {item.get('id')}")
                        print(f"Matched Motion/Action: {item.get('motion', 'No motion')}")
                        print(f"Matched Bill Status Code: {bill_status['billStatusCode']['code']}")
                        print(f"Matched Bill Status Name: {bill_status['billStatusCode']['name']}")
                        print(f"Matched Draft Short Title: {bill_data['draft']['shortTitle']}")
                        print("-" * 40)

if __name__ == "__main__":
    main()
