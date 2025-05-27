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
    HB 6
    HB 7
    HB 9
    HB 10
    HB 11
    HB 12
    HB 31
    HB 55
    HB 59
    HB 69
    HB 76
    HB 84
    HB 85
    HB 86
    HB 117
    HB 129
    HB 137
    HB 140
    HB 145
    HB 151
    HB 153
    HB 161
    HB 168
    HB 207
    HB 228
    HB 231
    HB 239
    HB 281
    HB 284
    HB 329
    HB 343
    HB 356
    HB 372
    HB 381
    HB 392
    HB 396
    HB 406
    HB 411
    HB 419
    HB 421
    HB 424
    HB 432
    HB 444
    HB 446
    HB 480
    HB 483
    HB 490
    HB 495
    HB 505
    HB 513
    HB 515
    HB 516
    HB 527
    HB 545
    HB 575
    HB 586
    HB 588
    HB 590
    HB 602
    HB 620
    HB 621
    HB 623
    HB 624
    HB 626
    HB 633
    HB 641
    HB 667
    HB 669
    HB 680
    HB 681
    HB 682
    HB 683
    HB 684
    HB 685
    HB 686
    HB 690
    HB 692
    HB 725
    HB 745
    HB 756
    HB 757
    HB 768
    HB 769
    HB 770
    HB 775
    HB 778
    HB 786
    HB 794
    HB 801
    HB 807
    HB 817
    HB 818
    HB 819
    HB 833
    HB 845
    HB 846
    HB 849
    HB 853
    HB 864
    HB 866
    HB 867
    HB 869
    HB 872
    HB 876
    HB 882
    HB 888
    HB 891
    HB 898
    HB 908
    HB 913
    HB 918
    HB 920
    HB 923
    HB 931
    HB 932
    HB 935
    HB 936
    HB 939
    HB 940
    HB 943
    HB 949
    HB 954
    HB 492
    HB 514
    HB 584
    HB 592
    HB 599
    HB 627
    HB 760
    HB 863
    HB 897
    HB 899
    HB 917
    HB 953
    SB 19
    SB 45
    SB 69
    SB 77
    SB 93
    SB 103
    SB 116
    SB 147
    SB 174
    SB 226
    SB 243
    SB 253
    SB 260
    SB 278
    SB 301
    SB 316
    SB 319
    SB 326
    SB 333
    SB 335
    SB 337
    SB 348
    SB 350
    SB 393
    SB 409
    SB 413
    SB 429
    SB 430
    SB 435
    SB 440
    SB 446
    SB 447
    SB 468
    SB 492
    SB 497
    SB 514
    SB 520
    SB 524
    SB 532
    SB 534
    SB 535
    SB 542
    SB 545
    SB 550
    SB 552
    SB 553
    SB 555
    SB 560
    SB 564
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
