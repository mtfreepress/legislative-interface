import requests
import os
import re
import json
import urllib.parse
from datetime import datetime
import argparse

# base URL
BASE_URL = 'https://api.legmt.gov'


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_bills(session_id):
    # load bill data from the json file
    json_file_path = os.path.join(get_script_dir(), f"list-bills-{session_id}.json")
    try:
        with open(json_file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: file not found at {json_file_path}")
        return []
    except json.JSONDecodeError:
        print("Error: failed to parse json.")
        return []


def list_files_in_directory(subdir):
    # list files in the directory for the given subdirectory under the centralized base directory
    base_dir = os.path.abspath(os.path.join(get_script_dir(), "..", "inputs"))
    vote_pdfs_dir = os.path.join(base_dir, "vote_pdfs", subdir)

    if os.path.exists(vote_pdfs_dir):
        # ignore hidden files
        files = [f for f in os.listdir(vote_pdfs_dir) if not f.startswith('.')]
        print(f"Visible files in directory '{vote_pdfs_dir}': {files}")
        return set(files)

# NOTE: Disabled for prod, too verbose
    # print(f"Directory '{vote_pdfs_dir}' does not exist.")
    return set()


def fetch_bill_vote_sheets(legislature_ordinal, session_ordinal, bill_type, bill_number):
    # fetch vote sheets for a specific bill
    url = f"{BASE_URL}/docs/v1/documents/getBillVoteSheets"
    params = {
        "legislatureOrdinal": legislature_ordinal,
        "sessionOrdinal": session_ordinal,
        "billType": bill_type.strip(),
        "billNumber": bill_number
    }
    print(url)
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"Fetched vote sheets: {response.json()}")
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching bill vote sheets: {e}")
        return []


def cache_and_download(all_votes, subdir):
    # compare existing files in the directory with the expected vote files and download missing ones
    existing_files = list_files_in_directory(subdir)
    expected_files = {vote['fileName'] for vote in all_votes if 'fileName' in vote}

    missing_files = expected_files - existing_files
    print(f"Missing files to download: {missing_files}")

    for vote in all_votes:
        document_id = vote.get('id')
        file_name = vote.get('fileName')
        if document_id and file_name and file_name in missing_files:
            pdf_url = get_short_pdf_url(document_id)
            if pdf_url:
                print(f"Downloading missing file: {file_name}")
                download_pdf(pdf_url, file_name, subdir)

    updated_files = list_files_in_directory(subdir)
    if expected_files == updated_files:
        print(f"All files are up-to-date in {subdir}.")
    else:
        print(f"Discrepancy found: expected {len(expected_files)} files, but found {len(updated_files)}.")


def get_short_pdf_url(document_id):
    # construct the url with the documentId as a query parameter
    url = f"{BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    headers = {'Accept': 'application/json, text/plain, */*'}

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        print(f"Error fetching short PDF URL for document {document_id}: {e}")
        return None


def download_pdf(pdf_url, file_name, subdir):
    # download the pdf using the url and save it in the specified subdirectory
    base_dir = os.path.abspath(os.path.join(get_script_dir(), "..", "inputs"))
    vote_pdfs_dir = os.path.join(base_dir, "vote_pdfs", subdir)
    os.makedirs(vote_pdfs_dir, exist_ok=True)

    output_path = os.path.join(vote_pdfs_dir, file_name)

    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as pdf_file:
            for chunk in response.iter_content(chunk_size=8192):
                pdf_file.write(chunk)
        print(f"Downloaded: {output_path}")
    except requests.RequestException as e:
        print(f"Error downloading PDF {file_name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Process legislative bills")
    parser.add_argument("--sessionId", type=int, required=True, help="Session ID")
    parser.add_argument("--legislatureOrdinal", type=int, required=True, help="Legislature ordinal")
    parser.add_argument("--sessionOrdinal", type=int, required=True, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    bills = load_bills(session_id)
    if not bills:
        print("No bills to process.")
        return

    for bill in bills:
        lc_number = bill['lc']
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        subdir = f"{bill_type}{bill_number}"

        print(f"Processing Bill: LC={lc_number}, Type={bill_type}, Number={bill_number}")

        vote_sheets = fetch_bill_vote_sheets(legislature_ordinal, session_ordinal, bill_type, bill_number)
        cache_and_download(vote_sheets, subdir)


if __name__ == "__main__":
    main()
