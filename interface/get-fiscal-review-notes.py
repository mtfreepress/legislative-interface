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
FISCAL_NOTES_FILE = os.path.join(BASE_DIR, "fiscal_notes.json")

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

def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, endpoint):
    url = f"{API_BASE_URL}/docs/v1/documents/{endpoint}"
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
        print(f"Error fetching document IDs: {response.status_code}")
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
    latest_date = None
    for document in documents:
        for attribute in document.get("attributes", []):
            if attribute["name"] == "SubmittedDate":
                date_str = attribute["stringValue"]
                date_formats = [
                    "%d/%m/%Y",
                    "%d/%m/%Y, %I:%M %p",
                    "%a %b %d %Y %H:%M:%S",
                    "%a %b %d %Y %H:%M:%S GMT%z" 
                ]
                for date_format in date_formats:
                    try:
                        # Remove timezone info before parsing
                        cleaned_date_str = date_str.split(" GMT")[0] if "GMT" in date_str else date_str
                        submitted_date = datetime.strptime(cleaned_date_str, date_format)
                        break
                    except ValueError:
                        continue
                else:
                    print(f"Error parsing date: {date_str}")
                    continue
                if latest_date is None or submitted_date > latest_date:
                    latest_date = submitted_date
                    latest_document = document
    return latest_document

def fetch_and_save_fiscal_notes(bill, legislature_ordinal, session_ordinal, download_dir, fiscal_notes, processed_bills):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, "getBillFiscalNotes")
    documents_rebuttals = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, "getBillFiscalNotesRebuttals")

    dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(dest_folder)

    latest_document = get_latest_document(documents)
    if latest_document:
        file_name = latest_document["fileName"]
        if file_name not in existing_files:
            document_id = latest_document["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, dest_folder, file_name)
            else:
                print(f"Failed to fetch PDF URL for document ID: {document_id}")
        fiscal_notes.append({"billType": bill_type, "billNumber": bill_number})
        processed_bills.add((bill_type, bill_number))
    else:
        # Remove existing files if no fiscal notes are found
        for file in existing_files:
            os.remove(os.path.join(dest_folder, file))
        # print(f"No fiscal notes found for {bill_type} {bill_number}. Removed existing files.")

def main():
    parser = argparse.ArgumentParser(description="Download fiscal notes for bills")
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

    download_dir = os.path.join(BASE_DIR, f"downloads/fiscal-note-pdfs-{session_id}")
    # print(f"Download directory: {download_dir}")

    fiscal_notes = load_json(FISCAL_NOTES_FILE)
    processed_bills = set()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_and_save_fiscal_notes, bill, legislature_ordinal, session_ordinal, download_dir, fiscal_notes, processed_bills) for bill in bills_data]
        for future in as_completed(futures):
            future.result()

    # Remove outdated fiscal notes
    fiscal_notes = [note for note in fiscal_notes if (note["billType"], note["billNumber"]) in processed_bills]

    save_json(fiscal_notes, FISCAL_NOTES_FILE)
    # print(f"Saved fiscal notes to {FISCAL_NOTES_FILE}")

if __name__ == "__main__":
    main()