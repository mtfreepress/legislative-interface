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
    parser.add_argument('legislative_session', type=str,
                        help="Legislative session identifier")
    return parser.parse_args()


def get_download_dir(legislative_session):
    path = os.path.join(BASE_DIR, f'downloads/raw-{legislative_session}-votes')
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


async def main_async(legislative_session, bills_path):
    download_dir = get_download_dir(legislative_session)
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
    legislative_session = args.legislative_session
    bills_path = os.path.join(
        BASE_DIR, f'../list-bills-{legislative_session}.json')
    asyncio.run(main_async(legislative_session, bills_path))


if __name__ == "__main__":
    main()
