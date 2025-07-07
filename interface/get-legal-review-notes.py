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
VETO_LETTER_FILE = os.path.join(BASE_DIR, "veto_letter.json")
VETO_LETTER_UPDATES_FILE = os.path.join(BASE_DIR, "veto_letter_updates.json")

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

def is_legal_note(document):
    return "Legal Review Note" in document.get("fileName", "")

def is_veto_letter(document):
    return "Veto" in document.get("fileName", "")

def get_latest_document(documents, filter_func):
    filtered = [doc for doc in documents if filter_func(doc)]
    if not filtered:
        return None
    return max(filtered, key=lambda d: d["id"])

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

def fetch_and_save_documents(
    bill, legislature_ordinal, session_ordinal,
    legal_note_dir, veto_letter_dir,
    legal_notes, legal_note_updates,
    veto_letters, veto_letter_updates,
    processed_bills
):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)

    # Legal Note
    legal_note_doc = get_latest_document(documents, is_legal_note)
    legal_note_folder = os.path.join(legal_note_dir, f"{bill_type}-{bill_number}")
    existing_legal_files = list_files_in_directory(legal_note_folder)
    if legal_note_doc:
        file_name = legal_note_doc["fileName"]
        if file_name not in existing_legal_files:
            for file in existing_legal_files:
                os.remove(os.path.join(legal_note_folder, file))
            document_id = legal_note_doc["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, legal_note_folder, file_name)
                legal_note_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
                processed_bills.add((bill_type, bill_number))
        legal_notes.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        for file in existing_legal_files:
            os.remove(os.path.join(legal_note_folder, file))

    # Veto Letter
    veto_letter_doc = get_latest_document(documents, is_veto_letter)
    veto_letter_folder = os.path.join(veto_letter_dir, f"{bill_type}-{bill_number}")
    existing_veto_files = list_files_in_directory(veto_letter_folder)
    if veto_letter_doc:
        file_name = veto_letter_doc["fileName"]
        if file_name not in existing_veto_files:
            for file in existing_veto_files:
                os.remove(os.path.join(veto_letter_folder, file))
            document_id = veto_letter_doc["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, veto_letter_folder, file_name)
                veto_letter_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        veto_letters.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        for file in existing_veto_files:
            os.remove(os.path.join(veto_letter_folder, file))

def main():
    parser = argparse.ArgumentParser(description="Download legal review notes and veto letters for bills")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    legal_note_dir = os.path.join(BASE_DIR, f"downloads/legal-note-pdfs-{session_id}")
    veto_letter_dir = os.path.join(BASE_DIR, f"downloads/veto-letter-pdfs-{session_id}")

    legal_notes = []
    legal_note_updates = []
    veto_letters = []
    veto_letter_updates = []
    processed_bills = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                fetch_and_save_documents,
                bill, legislature_ordinal, session_ordinal,
                legal_note_dir, veto_letter_dir,
                legal_notes, legal_note_updates,
                veto_letters, veto_letter_updates,
                processed_bills
            )
            for bill in bills_data
        ]
        for future in as_completed(futures):
            future.result()

    save_json(legal_notes, LEGAL_NOTES_FILE)
    print(f"Saved legal notes to {LEGAL_NOTES_FILE}")

    save_json(legal_note_updates, LEGAL_NOTE_UPDATES_FILE)
    print(f"Saved legal note updates to {LEGAL_NOTE_UPDATES_FILE}")

    save_json(veto_letters, VETO_LETTER_FILE)
    print(f"Saved veto letters to {VETO_LETTER_FILE}")

    save_json(veto_letter_updates, VETO_LETTER_UPDATES_FILE)
    print(f"Saved veto letter updates to {VETO_LETTER_UPDATES_FILE}")

if __name__ == "__main__":
    main()