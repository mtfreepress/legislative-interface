import os
import json
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

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
        print(f"Visible files in directory '{subdir}': {files}")
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

def fetch_and_save_legal_review_notes(bill, legislature_ordinal, session_ordinal, download_dir):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]
    print(f"Processing bill: {bill_type} {bill_number}")

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    expected_files = {document["fileName"] for document in documents if "legal" in document["fileName"].lower()}
    dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(dest_folder)

    missing_files = expected_files - existing_files
    print(f"Missing files to download: {missing_files}")

    for document in documents:
        if "legal" in document["fileName"].lower():
            file_name = document["fileName"]
            if file_name in missing_files:
                document_id = document["id"]
                pdf_url = fetch_pdf_url(session, document_id)
                if pdf_url:
                    print(f"Downloading file from: {pdf_url} to {dest_folder}/{file_name}")
                    download_file(pdf_url, dest_folder, file_name)

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
    print(f"Loading bills from: {list_bills_file}")
    bills_data = load_json(list_bills_file)
    print(f"Loaded {len(bills_data)} bills")

    download_dir = os.path.join(BASE_DIR, f"downloads/legal-note-pdfs-{session_id}")
    print(f"Download directory: {download_dir}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_and_save_legal_review_notes, bill, legislature_ordinal, session_ordinal, download_dir) for bill in bills_data]
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()