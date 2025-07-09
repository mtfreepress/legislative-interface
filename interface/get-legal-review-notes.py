import os
import json
import aiohttp
import asyncio
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "https://api.legmt.gov"
LEGAL_NOTES_FILE = os.path.join(BASE_DIR, "legal_notes.json")
LEGAL_NOTE_UPDATES_FILE = os.path.join(BASE_DIR, "legal-note-updates.json")
VETO_LETTER_FILE = os.path.join(BASE_DIR, "veto_letter.json")
VETO_LETTER_UPDATES_FILE = os.path.join(BASE_DIR, "veto_letter_updates.json")

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

async def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    url = f"{API_BASE_URL}/docs/v1/documents/getBillOther"
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
            print(f"Error fetching document IDs: {resp.status} for bill:{bill_type} {bill_number}")
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

async def fetch_and_save_documents(
    session, bill, legislature_ordinal, session_ordinal,
    legal_note_dir, veto_letter_dir,
    legal_notes, legal_note_updates,
    veto_letters, veto_letter_updates
):
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = await fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)

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
            pdf_url = await fetch_pdf_url(session, document_id)
            if pdf_url:
                await download_file(session, pdf_url, legal_note_folder, file_name)
                legal_note_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        else:
            # Debugging to make sure skipping existing files works correctly — Disable in production
            # print(f"Skipping legal note for {bill_type} {bill_number}: {file_name} already exists.")
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
            pdf_url = await fetch_pdf_url(session, document_id)
            if pdf_url:
                await download_file(session, pdf_url, veto_letter_folder, file_name)
                veto_letter_updates.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
        else:
            # Debugging to make sure skipping existing files works correctly — Disable in production
            # print(f"Skipping veto letter for {bill_type} {bill_number}: {file_name} already exists.")
            veto_letters.append({"billType": bill_type, "billNumber": bill_number, "fileName": file_name})
    else:
        for file in existing_veto_files:
            os.remove(os.path.join(veto_letter_folder, file))

def sort_notes(notes):
    return sorted(notes, key=lambda x: (x["billType"], x["billNumber"], x.get("fileName", "")))

async def main_async(session_id, legislature_ordinal, session_ordinal):
    list_bills_file = os.path.join(BASE_DIR, f"../list-bills-{session_id}.json")
    bills_data = load_json(list_bills_file)

    legal_note_dir = os.path.join(BASE_DIR, f"downloads/legal-note-pdfs-{session_id}")
    veto_letter_dir = os.path.join(BASE_DIR, f"downloads/veto-letter-pdfs-{session_id}")

    legal_notes = []
    legal_note_updates = []
    veto_letters = []
    veto_letter_updates = []

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        tasks = [
            fetch_and_save_documents(
                session, bill, legislature_ordinal, session_ordinal,
                legal_note_dir, veto_letter_dir,
                legal_notes, legal_note_updates,
                veto_letters, veto_letter_updates
            )
            for bill in bills_data
        ]
        await asyncio.gather(*tasks)

    # Sort all lists before saving
    legal_notes_sorted = sort_notes(legal_notes)
    legal_note_updates_sorted = sort_notes(legal_note_updates)
    veto_letters_sorted = sort_notes(veto_letters)
    veto_letter_updates_sorted = sort_notes(veto_letter_updates)

    save_json(legal_notes_sorted, LEGAL_NOTES_FILE)
    print(f"Saved legal notes to {LEGAL_NOTES_FILE}")

    save_json(legal_note_updates_sorted, LEGAL_NOTE_UPDATES_FILE)
    print(f"Saved legal note updates to {LEGAL_NOTE_UPDATES_FILE}")

    save_json(veto_letters_sorted, VETO_LETTER_FILE)
    print(f"Saved veto letters to {VETO_LETTER_FILE}")

    save_json(veto_letter_updates_sorted, VETO_LETTER_UPDATES_FILE)
    print(f"Saved veto letter updates to {VETO_LETTER_UPDATES_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Download legal review notes and veto letters for bills (async)")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()
    asyncio.run(main_async(args.sessionId, args.legislatureOrdinal, args.sessionOrdinal))

if __name__ == "__main__":
    main()