import os
import json
import aiohttp
import asyncio
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
FISCAL_NOTES_FILE = os.path.join(BASE_DIR, "fiscal_notes.json")
FISCAL_NOTE_UPDATES_FILE = os.path.join(BASE_DIR, "fiscal-note-updates.json")

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

def list_files_in_directory(subdir):
    if os.path.exists(subdir):
        files = [f for f in os.listdir(subdir) if not f.startswith('.')]
        return set(files)
    return set()

async def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, endpoint):
    url = f"{API_BASE_URL}/docs/v1/documents/{endpoint}"
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
            print(f"Error fetching document IDs: {resp.status} for bill: {bill_number} at {endpoint}")
            return []

async def fetch_pdf_url(session, document_id):
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    async with session.post(url) as resp:
        if resp.status == 200:
            return (await resp.text()).strip()
        else:
            print(f"Error fetching PDF URL for document {document_id}: {resp.status}")
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

def get_latest_document(documents):
    latest_document = None
    latest_id = None
    for document in documents:
        document_id = document["id"]
        if latest_id is None or document_id > latest_id:
            latest_id = document_id
            latest_document = document
    return latest_document

async def fetch_and_save_fiscal_notes(session, bill, legislature_ordinal, session_ordinal, download_dir, fiscal_notes, fiscal_note_updates):
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = await fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, "getBillFiscalNotes")
    documents_rebuttals = await fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number, "getBillFiscalNotesRebuttals")

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
            pdf_url = await fetch_pdf_url(session, document_id)
            if pdf_url:
                await download_file(session, pdf_url, dest_folder, file_name)
                fiscal_note_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
            else:
                print(f"Failed to fetch PDF URL for document ID: {document_id}")
        else:
            # Debug to make sure skipping existing files works correctly — Disable in production
            # print(f"Skipping {bill_type} {bill_number}: {file_name} already exists.")
            pass
        fiscal_notes.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        # Remove existing files if no fiscal notes are found
        for file in existing_files:
            os.remove(os.path.join(dest_folder, file))
        # print(f"No fiscal notes found for {bill_type} {bill_number}. Removed existing files.")

def sort_notes(notes):
    return sorted(notes, key=lambda x: (x["billType"], x["billNumber"], x.get("fileName", "")))

async def main_async(session_id, legislature_ordinal, session_ordinal):
    list_bills_file = os.path.join(BASE_DIR, f"list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)
    download_dir = os.path.join(BASE_DIR, f"downloads/fiscal-note-pdfs-{session_id}")

    fiscal_notes = []
    fiscal_note_updates = []

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        tasks = [
            fetch_and_save_fiscal_notes(session, bill, legislature_ordinal, session_ordinal, download_dir, fiscal_notes, fiscal_note_updates)
            for bill in bills_data
        ]
        await asyncio.gather(*tasks)

    # Sort before saving for consistency
    fiscal_notes_sorted = sort_notes(fiscal_notes)
    fiscal_note_updates_sorted = sort_notes(fiscal_note_updates)

    save_json(fiscal_notes_sorted, FISCAL_NOTES_FILE)
    print(f"Saved fiscal notes to {FISCAL_NOTES_FILE}")

    save_json(fiscal_note_updates_sorted, FISCAL_NOTE_UPDATES_FILE)
    print(f"Saved fiscal note updates to {FISCAL_NOTE_UPDATES_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Download fiscal notes for bills (async)")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()
    asyncio.run(main_async(args.sessionId, args.legislatureOrdinal, args.sessionOrdinal))

if __name__ == "__main__":
    main()