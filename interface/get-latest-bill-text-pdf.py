import os
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
BILL_TEXT_FILE = os.path.join(BASE_DIR, "bill_text.json")
BILL_TEXT_UPDATES_FILE = os.path.join(BASE_DIR, "bill_text_updates.json")

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

def get_latest_document(documents):
    if not documents:
        return None
    return max(documents, key=lambda d: d["id"])

def list_files_in_directory(subdir):
    if os.path.exists(subdir):
        files = [f for f in os.listdir(subdir) if not f.startswith('.')]
        return set(files)
    return set()

def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    url = f"{API_BASE_URL}/docs/v1/documents/getBillText"
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
        print(f"Error fetching bill text IDs: {response.status_code} for bill:{bill_type} {bill_number}")
        return []

def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    response = session.post(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Error fetching PDF URL for document {document_id}: {response.status_code}")
        return None

def fetch_and_save_bill_text(
    bill, legislature_ordinal, session_ordinal,
    bill_text_dir, bill_texts, bill_text_updates
):
    session = requests.Session()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    bill_text_doc = get_latest_document(documents)
    bill_text_folder = os.path.join(bill_text_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(bill_text_folder)
    if bill_text_doc:
        file_name = bill_text_doc["fileName"]
        if file_name not in existing_files:
            for file in existing_files:
                os.remove(os.path.join(bill_text_folder, file))
            document_id = bill_text_doc["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, bill_text_folder, file_name)
                bill_text_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        bill_texts.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        for file in existing_files:
            os.remove(os.path.join(bill_text_folder, file))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download bill text PDFs for bills")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    bill_text_dir = os.path.join(BASE_DIR, f"downloads/bill-text-pdfs-{session_id}")

    bill_texts = []
    bill_text_updates = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                fetch_and_save_bill_text,
                bill, legislature_ordinal, session_ordinal,
                bill_text_dir, bill_texts, bill_text_updates
            )
            for bill in bills_data
        ]
        for future in as_completed(futures):
            future.result()

    save_json(bill_texts, BILL_TEXT_FILE)
    print(f"Saved bill texts to {BILL_TEXT_FILE}")

    save_json(bill_text_updates, BILL_TEXT_UPDATES_FILE)
    print(f"Saved bill text updates to {BILL_TEXT_UPDATES_FILE}")

if __name__ == "__main__":
    main()