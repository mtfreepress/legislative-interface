#!/usr/bin/env python3
# filepath: bill_title_extractor.py
import json
import os
import sys
import argparse
import csv


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Extract short titles for bills")
    parser.add_argument(
        'date', help='Date for the output filename (e.g., 20250414)')
    args = parser.parse_args()

    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))

    base_dir = os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))  # Go up to root
    bills_dir = os.path.join(base_dir, "interface", "downloads", "raw-2-bills")
    output_dir = os.path.join(base_dir, "interface", "gianforte-bills")
    os.makedirs(output_dir, exist_ok=True)

    # Hardcoded list of bills - replace with your bills
    bills_input = """
    HB 102
    HB 114
    HB 122
    HB 123
    HB 126
    HB 130
    HB 141
    HB 151
    HB 166
    HB 180
    HB 184
    HB 193
    HB 201
    HB 208
    HB 217
    HB 226
    HB 251
    HB 266
    HB 267
    HB 269
    HB 270
    HB 276
    HB 285
    HB 291
    HB 292
    HB 293
    HB 296
    HB 307
    HB 311
    HB 312
    HB 318
    HB 324
    HB 325
    HB 328
    HB 330
    HB 333
    HB 336
    HB 337
    HB 342
    HB 344
    HB 352
    HB 367
    HB 380
    HB 387
    HB 391
    HB 393
    HB 394
    HB 397
    HB 398
    HB 400
    HB 401
    HB 413
    HB 414
    HB 415
    HB 423
    HB 428
    HB 430
    HB 435
    HB 438
    HB 442
    HB 443
    HB 447
    HB 450
    HB 454
    HB 455
    HB 458
    HB 463
    HB 464
    HB 466
    HB 467
    HB 468
    HB 471
    HB 473
    HB 474
    HB 475
    HB 476
    HB 486
    HB 487
    HB 491
    HB 493
    HB 496
    HB 502
    HB 503
    HB 504
    HB 520
    HB 521
    HB 523
    HB 530
    HB 531
    HB 544
    HB 591
    HB 595
    HB 600
    HB 603
    HB 612
    HB 614
    HB 616
    HB 625
    HB 629
    HB 631
    HB 632
    HB 638
    HB 642
    HB 648
    HB 651
    HB 655
    HB 656
    HB 664
    HB 671
    HB 694
    HB 710
    SB 105
    SB 111
    SB 161
    SB 163
    SB 166
    SB 221
    SB 487
    """

    # Clean up the input
    bills = [bill.strip()
             for bill in bills_input.strip().split('\n') if bill.strip()]

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
        json_file = os.path.join(
            bills_dir, f"{bill_type}-{bill_number}-raw-bill.json")

        try:
            # Read the JSON file
            with open(json_file, 'r') as f:
                bill_data = json.load(f)

            # Extract the short title
            short_title = bill_data.get('draft', {}).get(
                'shortTitle', 'No title available')

            # Add to dictionary (without space between type and number)
            bill_code = f"{bill_type}{bill_number}"
            bill_titles[bill_code] = short_title
            print(f"Found: {bill_code} - {short_title}")

        except FileNotFoundError:
            print(
                f"Warning: Could not find JSON file for bill {bill}: {json_file}")
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
