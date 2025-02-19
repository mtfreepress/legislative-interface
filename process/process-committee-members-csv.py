import os
import json
import csv
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMMITTEES_FILE = os.path.join(BASE_DIR, "../interface/downloads/all-committees-2.json")
LEGISLATORS_FILE = os.path.join(BASE_DIR, "../interface/downloads/legislators/legislators.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "./cleaned")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate committee membership CSV.")
    parser.add_argument("year", type=str, help="Year for the output CSV filename")
    return parser.parse_args()

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def get_legislator_name(legislator):
    return f"{legislator['lastName']}, {legislator['firstName']}"

def main():
    args = parse_arguments()
    year = args.year
    output_csv = os.path.join(OUTPUT_DIR, f"committee-assignments-{year}.csv")

    committees = load_json(COMMITTEES_FILE)
    legislators = {leg['id']: leg for leg in load_json(LEGISLATORS_FILE)}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(output_csv, "w", newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["committee", "lawmaker", "role"])

        for committee in committees:
            committee_key = committee["key"]
            if committee_key in ["senate-committee-of-the-whole", "house-committee-of-the-whole"]:
                continue
            for membership in committee.get("memberships", []):
                legislator_id = membership["legislatorId"]
                role = membership["type"]["name"].lower().replace(" ", "-")
                legislator = legislators.get(legislator_id)
                if legislator:
                    lawmaker_name = get_legislator_name(legislator)
                    csvwriter.writerow([committee_key, lawmaker_name, role])

if __name__ == "__main__":
    main()