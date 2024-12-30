import requests
import os
import re
import json
import urllib.parse
from datetime import datetime

session = 2

# base URL
BASE_URL = 'https://api.legmt.gov'
BILLS_JSON_PATH = f'./list-bills-{session}.json'

# load bill list from json to loop through


def load_bills():
    """
    Load bill data from the JSON file.
    """
    try:
        with open(BILLS_JSON_PATH, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found at {BILLS_JSON_PATH}")
        return []
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON.")
        return []


def list_files_in_directory(subdir):
    """
    List files in the directory for the given subdirectory under the centralized base directory.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inputs"))
    vote_pdfs_dir = os.path.join(base_dir, "vote_pdfs", subdir)
    
    if os.path.exists(vote_pdfs_dir):
        # Ignore hidden files
        files = [f for f in os.listdir(vote_pdfs_dir) if not f.startswith('.')]
        print(f"Visible files in directory '{vote_pdfs_dir}': {files}")
        return set(files)
    
    print(f"Directory '{vote_pdfs_dir}' does not exist.")
    return set()



def cache_and_download(all_votes, subdir):
    """
    Compare existing files in the directory with the expected vote files and download missing ones.
    """
    existing_files = list_files_in_directory(subdir)
    expected_files = {vote['fileName']
                      for vote in all_votes if 'fileName' in vote}

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
        print(f"Discrepancy found: expected {
              len(expected_files)} files, but found {len(updated_files)}.")


def fetch_bill_vote_sheets(legislature_ordinal, session_ordinal, bill_type, bill_number):
    """
    Fetch vote sheets for a specific bill.
    """
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


def process_bill_actions(session_ordinal, lc_number):
    """
    Fetches the bill's actions and processes the voteSeq and status item date to generate filenames.
    Returns a list of simplified documents.
    """
    url = f"{BASE_URL}/archive/v1/bills/{session_ordinal}/{lc_number}"

    filenames = []
    simplified_docs = []
    valid_filename_pattern = re.compile(
        r"^\d{3}\.\d{4}\.pdf$")

    try:
        response = requests.get(url)
        response.raise_for_status()

        bill_data = response.json()
        bill_actions = bill_data.get("billActions", [])
        print("\nProcessing vote sequences:")
        for action in bill_actions:
            vote_seq = action.get("voteSeq")
            status_item_date = action.get("date")
            chamber = action.get("actionType", {}).get(
                "description", "").split()[0]

            # skip actions with voteSeq that is None or "none" (case-insensitive) to only get actions with votes
            if vote_seq is None or (isinstance(vote_seq, str) and vote_seq.lower() == "none"):
                continue

            if status_item_date and chamber:
                # fetch leg chamber day
                leg_dd = fetch_legislative_calendar_day(
                    status_item_date.split('T')[0])
                if leg_dd:
                    # generate filenames
                    filename1, filename2 = generate_filenames(
                        vote_seq, chamber, leg_dd, status_item_date)

                    # make sure they match the pattern, if so, append
                    if filename1 and valid_filename_pattern.match(filename1):
                        filenames.append(filename1)
                    if filename2 and valid_filename_pattern.match(filename2):
                        filenames.append(filename2)

                    # fetch based on voteSeq to determine folder_id
                    if vote_seq.startswith('H'):
                        folder_id = "8340"  # House folder ID
                    elif vote_seq.startswith('S'):
                        folder_id = "8341"  # Senate folder ID
                    else:
                        folder_id = None

                    if folder_id:
                        docs = fetch_document_id_by_folder_id(
                            folder_id, filename1 or filename2)
                        if docs:
                            simplified_docs.extend(docs)
        return simplified_docs

    except requests.RequestException as e:
        print(f"Error fetching bill data: {e}")
        return []


def get_short_pdf_url(document_id):
    # construct the URL with the documentId as a query parameter
    url = f"{BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"

    headers = {
        'Accept': 'application/json, text/plain, */*',
    }

    try:
        # POST request
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        download_url = response.text.strip()
        return download_url
    except requests.RequestException as e:
        print(f"Error fetching short PDF URL for document {document_id}: {e}")
        return None


def download_pdf(pdf_url, file_name, subdir):
    """
    Download the PDF using the URL and save it in the specified subdirectory.
    """
    base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "inputs"))
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


def get_folder_id(legislature_ordinal, session_ordinal, bill_type, bill_number, vote_type):
    """
    Fetches the folder ID for either House or Senate floor votes.
    """
    path = f"{legislature_ordinal}/{session_ordinal}/Bills/FloorVotes/{vote_type}"
    encoded_path = urllib.parse.quote(path)

    url = f"{BASE_URL}/docs/v1/folders/findByPath?path={encoded_path}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # extract the folder ID from the response
        folder_data = response.json()
        folder_id = folder_data.get("id", None)
        if folder_id:
            print(f"Folder ID for {vote_type} floor votes: {folder_id}")
        else:
            print(f"No folder ID found for {vote_type} floor votes.")

        return folder_id
    except requests.RequestException as e:
        print(f"Error fetching {vote_type} floor vote directory: {e}")
        return None


def process_vote_seq(vote_seq):
    """
    Converts a voteSeq like 'S93' or 'H58' into '0093' or '0058' format.
    """
    if vote_seq and (vote_seq.startswith('S') or vote_seq.startswith('H')):
        return vote_seq[1:].zfill(4)
    return None


def fetch_legislative_calendar_day(date_lookup):
    """
    Fetches the legislative calendar day data for a given date.
    """
    # convert date to MM/DD/YYYY format
    formatted_date = datetime.strptime(
        date_lookup, '%Y-%m-%d').strftime('%m/%d/%Y')

    url = f"{BASE_URL}/archive/v1/legislativeCalendars/byDate"
    payload = {"date": formatted_date}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        if data:
            leg_dd = str(data[0]['id']['legDD']).zfill(
                3)  # Format legDD as 3 digits
            return leg_dd
        else:
            print(f"No legislative calendar data found for date: {
                  formatted_date}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching legislative calendar day: {e}")
        return None


def generate_filenames(vote_seq, chamber, leg_dd, status_item_date):
    """
    Generates filenames based on the voteSeq, chamber, legislative day (legDD), and status item date.
    """
    # ensure legDD is properly formatted as a 3-digit number
    formatted_leg_dd = str(leg_dd).zfill(3)

    # pattern 1: legDD.voteSeq
    formatted_seq = process_vote_seq(vote_seq)
    if formatted_seq:
        filename1 = f"{formatted_leg_dd}.{formatted_seq}.pdf"
    else:
        filename1 = None

    # pattern 2: legDD.voteSeq (use legDD and vote_seq instead of YMMDD)
    filename2 = f"{formatted_leg_dd}.{vote_seq}.pdf" if vote_seq else None

    return filename1, filename2


def fetch_document_id_by_folder_id(folder_id, file_name):
    """
    Fetches documents based on folder ID and file name, and prints the document ids.
    """
    url = f"{BASE_URL}/docs/v1/documents/listByFolderFileName?folderId={
        folder_id}&fileName={file_name}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # extract document data from response and mimic vote_sheets structure
        documents = response.json()
        simplified_docs = []
        if documents:
            for doc in documents:
                simplified_doc = {
                    'id': doc.get('id'),
                    'fileName': doc.get('fileName'),
                    'folderId': doc.get('folderId'),
                    'templateId': None,
                    'attributes': []
                }
                simplified_docs.append(simplified_doc)
                print(simplified_docs)
                return simplified_docs
        else:
            print(f"No documents found for {
                  file_name}.pdf in folder {folder_id}.")
    except requests.RequestException as e:
        print(f"Error fetching documents for folder {folder_id}: {e}")


def main():
    legislature_ordinal = 68
    session_ordinal = 20231

    bills = load_bills()
    if not bills:
        print("No bills to process.")
        return

    for bill in bills:
        lc_number = bill['lc']
        bill_type = bill['billType']
        bill_number = bill['billNumber']

        subdir = f"{bill_type}{bill_number}"

        print(f"Processing Bill: LC={lc_number}, Type={
              bill_type}, Number={bill_number}")

        # Fetch vote sheets and simplified docs
        vote_sheets = fetch_bill_vote_sheets(
            legislature_ordinal, session_ordinal, bill_type, bill_number)
        simplified_docs = process_bill_actions(session_ordinal, lc_number)

        # Combine all votes into a single list
        all_votes = vote_sheets + simplified_docs

        # Cache and download missing files
        cache_and_download(all_votes, subdir)


if __name__ == "__main__":
    main()
