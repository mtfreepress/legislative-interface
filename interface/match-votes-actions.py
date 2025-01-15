import os
import json
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

votes_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-votes")
bills_dir = os.path.join(BASE_DIR, "downloads/raw-{session_id}-bills")
list_bills_file = os.path.join(BASE_DIR, "../list-bills-2.json")
legislators_file = os.path.join(BASE_DIR, "../inputs/legislators/legislators.json")
output_dir = os.path.join(BASE_DIR, "downloads/matched-{session_id}-votes")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Match votes and bill statuses.")
    parser.add_argument("session_id", type=str, help="Legislative session ID")
    return parser.parse_args()

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def main():
    args = parse_arguments()
    session_id = args.session_id

    # load bill list and legislator json
    list_bills = load_json(list_bills_file)
    legislators = {leg['id']: leg for leg in load_json(legislators_file)}


    os.makedirs(output_dir.format(session_id=session_id), exist_ok=True)

    for bill in list_bills:
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        # paths to files:
        vote_file_path = os.path.join(votes_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-votes.json")
        bill_file_path = os.path.join(bills_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-bill.json")

        if not os.path.exists(vote_file_path) or not os.path.exists(bill_file_path):
            print(f"Missing files for {bill_type} {bill_number}. Skipping.")
            continue

        votes_data = load_json(vote_file_path)
        bill_data = load_json(bill_file_path)

        matched_votes = []

        for item in votes_data:
            bill_status_id = item.get('billStatus', {}).get('id') or item.get('billStatusId')
            if bill_status_id:
                for bill_status in bill_data.get('draft', {}).get('billStatuses', []):
                    if bill_status['id'] == bill_status_id:
                        # match legislator votes with their id/name
                        for vote in item.get('legislatorVotes', []):
                            legislator_id = vote.get('legislatorId')
                            if legislator_id is None:
                                print(f"Skipping vote without legislatorId: {vote}")
                                continue
                            legislator = legislators.get(legislator_id)
                            if legislator:
                                matched_votes.append({
                                    "legislator": f"{legislator['lastName']}, {legislator['firstName']}",
                                    "voteType": vote['voteType'],
                                    "votingMemberStatus": vote['votingMemberStatus']
                                })

# TODO: Delete later when not needed 
# debugging
    # bill_type = "HB"
    # bill_number = 1

    # vote_file_path = os.path.join(votes_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-votes.json")
    # bill_file_path = os.path.join(bills_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-raw-bill.json")

    # if not os.path.exists(vote_file_path) or not os.path.exists(bill_file_path):
    #     print(f"Missing files for {bill_type} {bill_number}. Skipping.")

    # votes_data = load_json(vote_file_path)
    # bill_data = load_json(bill_file_path)

    # matched_votes = []

    # for item in votes_data:
    #     bill_status_id = item.get('billStatus', {}).get('id') or item.get('billStatusId')
    #     if bill_status_id:
    #         for bill_status in bill_data.get('draft', {}).get('billStatuses', []):
    #             if bill_status['id'] == bill_status_id:
    #                 # Match legislator votes
    #                 for vote in item.get('legislatorVotes', []):
    #                     legislator_id = vote.get('legislatorId')  # Safely get 'legislatorId'
    #                     if legislator_id is None:
    #                         print(f"Skipping vote without legislatorId: {vote}")
    #                         continue
    #                     legislator = legislators.get(legislator_id)
    #                     print(legislator)
    #                     if legislator:
    #                         matched_votes.append({
    #                             "legislator": f"{legislator['lastName']}, {legislator['firstName']}",
    #                             "voteType": vote['voteType'],
    #                             "votingMemberStatus": vote['votingMemberStatus']
    #                         })


        output_file_path = os.path.join(output_dir.format(session_id=session_id), f"{bill_type}-{bill_number}-matched-votes.json")
        with open(output_file_path, "w") as f:
            json.dump({
                "billId": bill_data['id'],
                "billStatusId": bill_status_id,
                "legislatorVotes": matched_votes
            }, f, indent=2)

        # print(f"Processed {bill_type} {bill_number}, results saved to {output_file_path}.")

if __name__ == "__main__":
    main()