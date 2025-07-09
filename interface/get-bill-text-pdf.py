import os
import json
import aiohttp
import asyncio
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
BILL_PDFS_FILE = os.path.join(BASE_DIR, "bill_pdfs.json")
BILL_PDF_UPDATES_FILE = os.path.join(BASE_DIR, "bill_pdf_updates.json")

headers = {
    "User-Agent": "MTFP-Legislative-Scraper/1.0 (+https://montanafreepress.org/contact/)"
}

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_json(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

async def fetch_bill_versions(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    url = f"{API_BASE_URL}/docs/v1/documents/getBillVersions"
    async with session.get(url, params=params) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            print(f"Failed to fetch bill versions: {resp.status}")
            return []

def sort_bill_versions(versions):
    def version_key(version):
        parts = version["fileName"].split("_")
        if len(parts) == 2:
            file_name, numeric_part = parts
            is_x = numeric_part.lower().startswith("x")
            try:
                num = -float('inf') if is_x else int(numeric_part.split('.')[0])
            except ValueError:
                num = -float('inf')
            return (file_name, is_x, num)
        else:
            return (version["fileName"], True, -float('inf'))
    return sorted(versions, key=version_key, reverse=True)

async def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    async with session.post(url) as resp:
        if resp.status == 200:
            return (await resp.text()).strip()
        else:
            print(f"Failed to fetch PDF URL for document ID: {document_id} with status code {resp.status}")
            return None

async def download_file(session, url, dest_folder, file_name):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    file_path = os.path.join(dest_folder, file_name)
    async with session.get(url) as resp:
        if resp.status == 200:
            with open(file_path, "wb") as f:
                f.write(await resp.read())
            print(f"Downloaded: {file_path}")
        else:
            print(f"Failed to download: {url} with status code {resp.status}")

async def fetch_and_save_bill_text(session, bill, legislature_ordinal, session_ordinal, download_dir, bill_pdfs, bill_pdf_updates):
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    versions = await fetch_bill_versions(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    sorted_versions = sort_bill_versions(versions)
    file_version_to_use = sorted_versions[0] if sorted_versions else None

    if file_version_to_use:
        file_name = file_version_to_use["fileName"]
        dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
        local_file_path = os.path.join(dest_folder, file_name)

        if os.path.exists(local_file_path):
            print(f"File {local_file_path} already exists locally. Skipping download.")
            bill_pdfs.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
            return

        short_pdf_url = await fetch_pdf_url(session, file_version_to_use['id'])
        if short_pdf_url:
            await download_file(session, short_pdf_url, dest_folder, file_name)
            bill_pdf_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
            bill_pdfs.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        else:
            print(f"No valid PDF URL found for {bill_type} {bill_number}")
    else:
        print(f"No valid bill version found for {bill_type} {bill_number}")

async def main_async(session_id, legislature_ordinal, session_ordinal):
    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)
    download_dir = os.path.join(DOWNLOAD_DIR, f"bill-text-{session_id}")

    connector = aiohttp.TCPConnector(limit=10) 
    bill_pdfs = []
    bill_pdf_updates = []
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_and_save_bill_text(session, bill, legislature_ordinal, session_ordinal, download_dir, bill_pdfs, bill_pdf_updates)
            for bill in bills_data
        ]
        await asyncio.gather(*tasks)

    save_json(bill_pdfs, BILL_PDFS_FILE)
    print(f"Saved bill PDFs to {BILL_PDFS_FILE}")

    save_json(bill_pdf_updates, BILL_PDF_UPDATES_FILE)
    print(f"Saved bill PDF updates to {BILL_PDF_UPDATES_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Download bill texts for bills (async)")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()
    asyncio.run(main_async(args.sessionId, args.legislatureOrdinal, args.sessionOrdinal))

if __name__ == "__main__":
    main()