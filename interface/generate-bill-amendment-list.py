import os
import json
from collections import defaultdict

def main():
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to amendments.json (in same directory as script)
    amendments_file = os.path.join(script_dir, "amendments.json")
    
    # Output file path
    output_file = os.path.join(script_dir, "bills-with-amendments.txt")
    
    # Read amendments data
    try:
        with open(amendments_file, 'r') as f:
            amendments = json.load(f)
    except Exception as e:
        print(f"Error reading amendments.json: {e}")
        return
    
    # Extract unique bill identifiers
    unique_bills = set()
    for amendment in amendments:
        if "billType" in amendment and "billNumber" in amendment:
            bill_identifier = f"{amendment['billType']} {amendment['billNumber']}"
            unique_bills.add(bill_identifier)
    
    # Sort the bills by type and number
    sorted_bills = sorted(unique_bills, key=lambda x: (x.split()[0], int(x.split()[1])))
    
    # Write to output file
    try:
        with open(output_file, 'w') as f:
            for bill in sorted_bills:
                f.write(f"{bill}\n")
        print(f"Successfully created {output_file} with {len(sorted_bills)} bills")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()