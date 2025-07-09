import os
import re
import json
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
BILL_PDFS_FILE = os.path.join(BASE_DIR, "bill_pdfs.json")
BILL_PDF_UPDATES_FILE = os.path.join(BASE_DIR, "bill_pdf_updates.json")

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

def get_filename_from_cd(cd, default):
    if not cd:
        return default
    fname = re.findall('filename="?([^"]+)"?', cd)
    return fname[0] if fname else default

def fetch_and_save_bill_pdf(
    bill, legislature_ordinal, session_ordinal,
    bill_text_dir, bill_pdfs, bill_pdf_updates, processed_bills
):
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    url = f"{API_BASE_URL}/docs/v1/documents/getBillText"
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    bill_folder = os.path.join(bill_text_dir, f"{bill_type}-{bill_number}")
    if not os.path.exists(bill_folder):
        os.makedirs(bill_folder)

    response = session.get(url, params=params)
    if response.status_code == 200:
        # Get filename from Content-Disposition header if available
        cd = response.headers.get("Content-Disposition")
        default_name = f"{bill_type}-{bill_number}.pdf"
        file_name = get_filename_from_cd(cd, default_name)
        file_path = os.path.join(bill_folder, file_name)

        # Only download if file does not exist or is different
        should_download = True
        if os.path.exists(file_path):
            # Compare file sizes as a quick check
            local_size = os.path.getsize(file_path)
            remote_size = int(response.headers.get("Content-Length", -1))
            if remote_size == local_size and remote_size > 0:
                should_download = False

        if should_download:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded: {file_path}")
            bill_pdf_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        else:
            print(f"Skipped (already up-to-date): {file_path}")

        processed_bills.add((bill_type, bill_number))
        bill_pdfs.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        print(f"Failed to download PDF for {bill_type} {bill_number}: {response.status_code} {response.headers.get('Content-Type')}")

def main():
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

    bill_pdfs = []
    bill_pdf_updates = []
    processed_bills = set()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(
                fetch_and_save_bill_pdf,
                bill, legislature_ordinal, session_ordinal,
                bill_text_dir, bill_pdfs, bill_pdf_updates, processed_bills
            )
            for bill in bills_data
        ]
        for future in as_completed(futures):
            future.result()

    save_json(bill_pdfs, BILL_PDFS_FILE)
    print(f"Saved bill PDFs to {BILL_PDFS_FILE}")

    save_json(bill_pdf_updates, BILL_PDF_UPDATES_FILE)
    print(f"Saved bill PDF updates to {BILL_PDF_UPDATES_FILE}")

if __name__ == "__main__":
    main()