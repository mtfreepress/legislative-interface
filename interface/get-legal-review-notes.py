import os
import json
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
LEGAL_NOTES_FILE = os.path.join(BASE_DIR, "legal_notes.json")
LEGAL_NOTE_UPDATES_FILE = os.path.join(BASE_DIR, "legal-note-updates.json")

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_json(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def download_file(url, dest_folder, file_name):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    response = requests.get(url)
    if response.status_code == 200:
        file_path = os.path.join(dest_folder, file_name)
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {file_path}")
    else:
        print(f"Failed to download: {url}")

def list_files_in_directory(subdir):
    if os.path.exists(subdir):
        files = [f for f in os.listdir(subdir) if not f.startswith('.')]
        return set(files)
    return set()

def create_session_with_retries():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    url = f"{API_BASE_URL}/docs/v1/documents/getBillOther"
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    response = session.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching document IDs: {response.status_code} for bill:{bill_type} {bill_number}")
        return []

def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    response = session.post(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Error fetching PDF URL for document {document_id}: {response.status_code}")
        return None

def get_latest_document(documents):
    latest_document = None
    latest_id = None
    for document in documents:
        document_id = document["id"]
        if latest_id is None or document_id > latest_id:
            latest_id = document_id
            latest_document = document
    return latest_document

def fetch_and_save_legal_review_notes(bill, legislature_ordinal, session_ordinal, download_dir, legal_notes, legal_note_updates, processed_bills):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(dest_folder)

    latest_document = get_latest_document(documents)
    if latest_document:
        file_name = latest_document["fileName"]
        if file_name not in existing_files:
            # Remove older files
            for file in existing_files:
                os.remove(os.path.join(dest_folder, file))
            document_id = latest_document["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, dest_folder, file_name)
                legal_note_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
                processed_bills.add((bill_type, bill_number))
            else:
                print(f"Failed to fetch PDF URL for document ID: {document_id}")
        legal_notes.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        # Remove existing files if no legal notes are found
        for file in existing_files:
            os.remove(os.path.join(dest_folder, file))
        # print(f"No legal notes found for {bill_type} {bill_number}. Removed existing files.")

def main():
    parser = argparse.ArgumentParser(description="Download legal review notes for bills")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    # debugging:
    # bills_data = [
    #     {
    #         "lc": "LC0710",
    #         "id": 710,
    #         "billType": "HB",
    #         "billNumber": 5
    #     },
    # ]

    download_dir = os.path.join(BASE_DIR, f"downloads/legal-note-pdfs-{session_id}")
    # print(f"Download directory: {download_dir}")

    legal_notes = []
    legal_note_updates = []
    processed_bills = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_and_save_legal_review_notes, bill, legislature_ordinal, session_ordinal, download_dir, legal_notes, legal_note_updates, processed_bills) for bill in bills_data]
        for future in as_completed(futures):
            future.result()

    # Save legal_notes.json
    save_json(legal_notes, LEGAL_NOTES_FILE)
    print(f"Saved legal notes to {LEGAL_NOTES_FILE}")

    # Save legal-note-updates.json
    save_json(legal_note_updates, LEGAL_NOTE_UPDATES_FILE)
    print(f"Saved legal note updates to {LEGAL_NOTE_UPDATES_FILE}")

if __name__ == "__main__":
    main()