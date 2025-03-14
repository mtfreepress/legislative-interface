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
AMENDMENTS_FILE = os.path.join(BASE_DIR, "amendments.json")
AMENDMENT_UPDATES_FILE = os.path.join(BASE_DIR, "amendment-updates.json")

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
        return True
    else:
        print(f"Failed to download: {url}")
        return False

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

def fetch_amendment_documents(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    url = f"{API_BASE_URL}/docs/v1/documents/getBillAmendments"
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
        print(f"Error fetching amendment documents: {response.status_code} for bill:{bill_type} {bill_number}")
        return []

def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    response = session.post(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Error fetching PDF URL for document {document_id}: {response.status_code}")
        return None

def fetch_and_save_amendments(bill, legislature_ordinal, session_ordinal, download_dir, amendments, amendment_updates, processed_bills):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    amendment_documents = fetch_amendment_documents(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    
    if not amendment_documents:
        return
    
    bill_amendments = []
    bill_amendment_updates = []
    
    # Sort documents into full and condensed versions
    full_amendments = [doc for doc in amendment_documents if not doc["fileName"].lower().endswith("-condensed.pdf")]
    condensed_amendments = [doc for doc in amendment_documents if doc["fileName"].lower().endswith("-condensed.pdf")]
    
    dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(dest_folder)
    
    # Process all amendments (both full and condensed)
    for amendment in amendment_documents:
        document_id = amendment["id"]
        file_name = amendment["fileName"]
        
        # Check if file already exists
        if file_name not in existing_files:
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                if download_file(pdf_url, dest_folder, file_name):
                    bill_amendment_updates.append({
                        "billType": bill_type,
                        "billNumber": bill_number,
                        "fileName": file_name,
                        "id": document_id,
                        "isCondensed": file_name.lower().endswith("-condensed.pdf")
                    })
            else:
                print(f"Failed to fetch PDF URL for amendment ID: {document_id}")
        
        # Add to full amendments list regardless of download status
        bill_amendments.append({
            "billType": bill_type,
            "billNumber": bill_number,
            "fileName": file_name,
            "id": document_id,
            "isCondensed": file_name.lower().endswith("-condensed.pdf")
        })
    
    # Add to our global tracking lists if we found amendments
    if bill_amendments:
        amendments.extend(bill_amendments)
        amendment_updates.extend(bill_amendment_updates)
        processed_bills.add((bill_type, bill_number))
        print(f"Processed {len(bill_amendments)} amendments for {bill_type} {bill_number}")

def main():
    parser = argparse.ArgumentParser(description="Download bill amendments")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    download_dir = os.path.join(BASE_DIR, f"downloads/amendment-pdfs-{session_id}")
    print(f"Download directory: {download_dir}")

    amendments = []
    amendment_updates = []
    processed_bills = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_and_save_amendments, bill, legislature_ordinal, session_ordinal, download_dir, amendments, amendment_updates, processed_bills) for bill in bills_data]
        for future in as_completed(futures):
            future.result()

    # Save amendments.json
    save_json(amendments, AMENDMENTS_FILE)
    print(f"Saved amendments to {AMENDMENTS_FILE}")

    # Save amendment-updates.json
    save_json(amendment_updates, AMENDMENT_UPDATES_FILE)
    print(f"Saved amendment updates to {AMENDMENT_UPDATES_FILE}")
    
    print(f"Processed amendments for {len(processed_bills)} bills")

if __name__ == "__main__":
    main()