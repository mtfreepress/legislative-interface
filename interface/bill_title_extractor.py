#!/usr/bin/env python3
# filepath: bill_title_extractor.py
import json
import os
import sys
import argparse
import csv

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Extract short titles for bills")
    parser.add_argument('date', help='Date for the output filename (e.g., 20250414)')
    args = parser.parse_args()
    
    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to root
    bills_dir = os.path.join(base_dir, "interface", "downloads", "raw-2-bills")
    output_dir = os.path.join(base_dir, "interface", "gianforte-bills")
    os.makedirs(output_dir, exist_ok=True)
    
    # Hardcoded list of bills - replace with your bills
    bills_input = """
    HB 3
    HB 16
    HB 18
    HB 20
    HB 24
    HB 28
    HB 37
    HB 46
    HB 49
    HB 53
    HB 68
    HB 77
    HB 82
    HB 89
    HB 91
    HB 92
    HB 106
    HB 108
    HB 109
    HB 120
    HB 136
    HB 144
    HB 146
    HB 150
    HB 157
    HB 159
    HB 164
    HB 165
    HB 175
    HB 190
    HB 191
    HB 196
    HB 197
    HB 210
    HB 214
    HB 215
    HB 235
    HB 249
    HB 257
    HB 268
    HB 335
    HB 426
    HB 434
    """
    
    # Clean up the input
    bills = [bill.strip() for bill in bills_input.strip().split('\n') if bill.strip()]
    
    # Dictionary to store bill codes and their titles
    bill_titles = {}
    
    # Process each bill
    for bill in bills:
        # Parse bill type and number
        parts = bill.split()
        if len(parts) != 2:
            print(f"Warning: Skipping invalid bill format: {bill}")
            continue
        
        bill_type, bill_number = parts
        
        # Create the path to the JSON file
        json_file = os.path.join(bills_dir, f"{bill_type}-{bill_number}-raw-bill.json")
        
        try:
            # Read the JSON file
            with open(json_file, 'r') as f:
                bill_data = json.load(f)
            
            # Extract the short title
            short_title = bill_data.get('draft', {}).get('shortTitle', 'No title available')
            
            # Add to dictionary (without space between type and number)
            bill_code = f"{bill_type}{bill_number}"
            bill_titles[bill_code] = short_title
            print(f"Found: {bill_code} - {short_title}")
            
        except FileNotFoundError:
            print(f"Warning: Could not find JSON file for bill {bill}: {json_file}")
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in file for bill {bill}")
        except Exception as e:
            print(f"Error processing bill {bill}: {str(e)}")
    
    # Write the output to a JSON file
    output_file = os.path.join(output_dir, f"bills-signed-{args.date}.json")
    with open(output_file, 'w') as f:
        json.dump(bill_titles, f, indent=4)
    
    # Add CSV output
    csv_output_file = os.path.join(output_dir, f"bills-signed-{args.date}.csv")
    with open(csv_output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write header
        csv_writer.writerow(['Bill Name', 'Bill Title'])
        # Write data
        for bill_code, title in bill_titles.items():
            # Format bill name with a space (e.g., "HB 3" instead of "HB3")
            bill_name = f"{bill_code[:2]} {bill_code[2:]}"
            csv_writer.writerow([bill_name, title])
    
    print(f"\nOutput written to {output_file}")
    print(f"CSV also written to {csv_output_file}")

if __name__ == "__main__":
    main()