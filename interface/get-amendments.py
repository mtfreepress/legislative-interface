import os
import json
import aiohttp
import asyncio
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
AMENDMENTS_FILE = os.path.join(BASE_DIR, "amendments.json")
AMENDMENT_UPDATES_FILE = os.path.join(BASE_DIR, "amendment-updates.json")

HEADERS = {
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


async def download_file(session, url, dest_folder, file_name):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    file_path = os.path.join(dest_folder, file_name)
    async with session.get(url) as resp:
        if resp.status == 200:
            with open(file_path, "wb") as f:
                f.write(await resp.read())
            # print(f"Downloaded: {file_path}")
            return True
        else:
            # print(f"Failed to download: {url}")
            return False


def list_files_in_directory(subdir):
    if os.path.exists(subdir):
        files = [f for f in os.listdir(subdir) if not f.startswith('.')]
        return set(files)
    return set()


def get_base_filename(filename):
    """Extract base filename without the (N) suffix"""
    import re
    pattern = r'^(.+?)(?:\([0-9]+\))?(\.[^.]+)$'
    match = re.match(pattern, filename)
    if match:
        base_name = match.group(1)
        extension = match.group(2)
        return base_name + extension
    return filename


def group_amendments_by_base_name(amendments):
    """Group amendments by their base filename and select primary version"""
    grouped = {}
    for amendment in amendments:
        file_name = amendment["fileName"]
        base_name = get_base_filename(file_name)
        if base_name not in grouped:
            grouped[base_name] = []
        grouped[base_name].append(amendment)
    primary_amendments = []
    for base_name, versions in grouped.items():
        primary = next(
            (v for v in versions if v["fileName"] == base_name), None)
        if not primary:
            primary = max(versions, key=lambda x: x["id"])
        primary_amendments.append(primary)
    return primary_amendments


async def fetch_amendment_documents(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    url = f"{API_BASE_URL}/docs/v1/documents/getBillAmendments"
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    async with session.get(url, params=params) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            print(
                f"Error fetching amendment documents: {resp.status} for bill:{bill_type} {bill_number}")
            return []


async def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    async with session.post(url) as resp:
        if resp.status == 200:
            return (await resp.text()).strip()
        else:
            print(
                f"Error fetching PDF URL for document {document_id}: {resp.status}")
            return None


async def fetch_and_save_amendments(
    session, bill, legislature_ordinal, session_ordinal, download_dir, amendments, amendment_updates, processed_bills
):
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    amendment_documents = await fetch_amendment_documents(
        session, legislature_ordinal, session_ordinal, bill_type, bill_number)

    if not amendment_documents:
        return

    unique_amendments = group_amendments_by_base_name(amendment_documents)
    bill_amendments = []
    bill_amendment_updates = []

    dest_folder = os.path.join(download_dir, f"{bill_type}-{bill_number}")
    existing_files = list_files_in_directory(dest_folder)
    existing_base_files = {get_base_filename(file) for file in existing_files}

    for amendment in unique_amendments:
        document_id = amendment["id"]
        file_name = amendment["fileName"]
        base_name = get_base_filename(file_name)

        # Check if any version of this file already exists
        if base_name not in existing_base_files:
            pdf_url = await fetch_pdf_url(session, document_id)
            if pdf_url:
                if await download_file(session, pdf_url, dest_folder, file_name):
                    bill_amendment_updates.append({
                        "billType": bill_type,
                        "billNumber": bill_number,
                        "fileName": file_name,
                        "id": document_id,
                        "isCondensed": file_name.lower().endswith("-condensed.pdf")
                    })
            else:
                print(
                    f"Failed to fetch PDF URL for amendment ID: {document_id}")
        else:
            # Debugging to make sure skipping existing files works correctly — Disable in production
            # print(f"Skipping {bill_type} {bill_number}: {file_name} already exists.")

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
        # print(f"Processed {len(bill_amendments)} amendments for {bill_type} {bill_number}")


def sort_amendments(amendments_list):
    """Sort amendments by bill type (alphabetically) and then by bill number (numerically)"""
    return sorted(amendments_list, key=lambda x: (x.get("billType", ""), x.get("billNumber", 0)))


async def main_async(session_id, legislature_ordinal, session_ordinal):
    list_bills_file = os.path.join(
        BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)
    download_dir = os.path.join(
        BASE_DIR, f"downloads/amendment-pdfs-{session_id}")
    # print(f"Download directory: {download_dir}")

    amendments = []
    amendment_updates = []
    processed_bills = set()

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        tasks = [
            fetch_and_save_amendments(
                session, bill, legislature_ordinal, session_ordinal,
                download_dir, amendments, amendment_updates, processed_bills
            )
            for bill in bills_data
        ]
        await asyncio.gather(*tasks)

    # Sort the amendments before saving
    sorted_amendments = sort_amendments(amendments)
    sorted_updates = sort_amendments(amendment_updates)

    # Save amendments.json
    save_json(sorted_amendments, AMENDMENTS_FILE)
    # print(f"Saved {len(sorted_amendments)} amendments to {AMENDMENTS_FILE} (sorted by bill type and number)")

    # Save amendment-updates.json
    save_json(sorted_updates, AMENDMENT_UPDATES_FILE)
    # print(f"Saved {len(sorted_updates)} amendment updates to {AMENDMENT_UPDATES_FILE} (sorted by bill type and number)")

    # print(f"Processed amendments for {len(processed_bills)} bills")


def main():
    parser = argparse.ArgumentParser(
        description="Download bill amendments (async)")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int,
                        help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()
    asyncio.run(main_async(args.sessionId,
                args.legislatureOrdinal, args.sessionOrdinal))


if __name__ == "__main__":
    main()
