import os
import json
import requests
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode


## This fetches all bill text versions. May be useful if we want a list of all versions of a bill.
## using get-latest-bill-text-pdf.py instead will fetch the latest version of the bill text PDF.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

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
        print(f"Failed to download: {url} with status code {response.status_code}")

def fetch_bill_versions(legislature_ordinal, session_ordinal, bill_type, bill_number):
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    url = f"{API_BASE_URL}/docs/v1/documents/getBillVersions?{urlencode(params)}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch bill versions: {response.status_code}")
        return []

def sort_bill_versions(versions):
    def version_key(version):
        file_name, numeric_part = version["fileName"].split("_")
        is_x = numeric_part.lower().startswith("x")
        try:
            num = -float('inf') if is_x else int(numeric_part.split('.')[0])
        except ValueError:
            num = -float('inf')
        return (file_name, is_x, num)
    
    return sorted(versions, key=version_key, reverse=True)

def fetch_pdf_url(document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    response = requests.post(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Failed to fetch PDF URL for document ID: {document_id} with status code {response.status_code}")
        return None

def fetch_and_save_bill_text(bill, legislature_ordinal, session_ordinal, download_dir):
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    versions = fetch_bill_versions(legislature_ordinal, session_ordinal, bill_type, bill_number)
    sorted_versions = sort_bill_versions(versions)
    file_version_to_use = sorted_versions[0] if sorted_versions else None

    if file_version_to_use:
        file_name = file_version_to_use["fileName"]
        dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
        local_file_path = os.path.join(dest_folder, file_name)

        # Check if the file already exists locally
        if os.path.exists(local_file_path):
            print(f"File {local_file_path} already exists locally. Skipping download.")
            return

        short_pdf_url = fetch_pdf_url(file_version_to_use['id'])
        if short_pdf_url:
            download_file(short_pdf_url, dest_folder, file_name)
        else:
            print(f"No valid PDF URL found for {bill_type} {bill_number}")
    else:
        print(f"No valid bill version found for {bill_type} {bill_number}")

def main():
    parser = argparse.ArgumentParser(description="Download bill texts for bills")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    download_dir = os.path.join(DOWNLOAD_DIR, f"bill-text-{session_id}")
# TODO: Play wwith the number of workers to see if we can push it higher to speed things up
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_and_save_bill_text, bill, legislature_ordinal, session_ordinal, download_dir) for bill in bills_data]
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()