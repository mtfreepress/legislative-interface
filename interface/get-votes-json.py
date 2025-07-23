import os
import json
import aiohttp
import asyncio
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS = {
    "User-Agent": "MTFP-Legislative-Scraper/1.0 (+https://montanafreepress.org/contact/)"
}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Fetch and save vote data for bills (async).")
    parser.add_argument('session_id', type=str,
                        help="Legislative session identifier")
    return parser.parse_args()


def get_download_dir(session_id):
    path = os.path.join(BASE_DIR, f'downloads/raw-{session_id}-votes')
    os.makedirs(path, exist_ok=True)
    return path


def load_bills(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


async def fetch_data(session, url):
    async with session.get(url) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            print(f"Failed to fetch data: {url} with status {resp.status}")
            return None


async def save_vote_data(data, bill_type, bill_number, download_dir):
    file_name = f"{bill_type}-{bill_number}-raw-votes.json"
    file_path = os.path.join(download_dir, file_name)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


async def fetch_and_save_vote_data(session, bill, download_dir):
    lc_number = bill['id']
    bill_type = bill['billType']
    bill_number = bill['billNumber']
    try:
        vote_data_url = f"https://api.legmt.gov/bills/v1/votes/findByBillId?billId={lc_number}"
        vote_data = await fetch_data(session, vote_data_url)
        if vote_data is not None:
            await save_vote_data(vote_data, bill_type, bill_number, download_dir)
            # too verbose for production
            # print(f"Saved votes for {bill_type}{bill_number}")
        else:
            # too verbose for production
            # print(f"No vote data for {bill_type}{bill_number}")
            pass
    except Exception as e:
        print(f"Failed to fetch data for {bill_type}{bill_number}: {e}")


async def main_async(session_id, bills_path):
    download_dir = get_download_dir(session_id)
    bills = load_bills(bills_path)
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        tasks = [
            fetch_and_save_vote_data(session, bill, download_dir)
            for bill in bills
        ]
        await asyncio.gather(*tasks)


def main():
    args = parse_arguments()
    session_id = args.session_id
    bills_path = os.path.join(
        BASE_DIR, f'list-bills-{session_id}.json')
    asyncio.run(main_async(session_id, bills_path))


if __name__ == "__main__":
    main()
