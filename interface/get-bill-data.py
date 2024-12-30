import os
import json
import requests

# TODO: 2023 - testing purposes only

# 2023 API URL and headers
# bills_url = "https://api.legmt.gov/archive/v1/bills/search?limit=9999&offset=0"
# headers = {
#     "Accept": "application/json, text/plain, */*",
#     "Content-Type": "application/json",
#     "Origin": "https://bills.legmt.gov",
#     "Referer": "https://bills.legmt.gov/",
# }

# 2023 sessionId, 2025 is using `2` rather than 20251
# session_id = 20231
# 2023 - Changed for 2025
# payload = {"sessionId": session_id, "sortBy": "billNumber"}

# --- 2025 API is different --- 
bills_url = "https://api.legmt.gov/bills/v1/bills/search?includeCounts=true&sort=billType.code,desc&sort=billNumber,asc&sort=draft.draftNumber,asc&limit=9999&offset=0"
headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://bills.legmt.gov",
    "Referer": "https://bills.legmt.gov/",
}

# 2025
session_id = 2

# wrap session_id in a list, use format that for some reason changed
payload = {"sessionIds": [session_id]}

# fetch bills data
def fetch_bills():
    response = requests.post(bills_url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch bills. HTTP Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


if __name__ == "__main__":
    # create downloads directory if it doesn't exist
    downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    # bills data
    bills_data = fetch_bills()
    if bills_data is not None:
        # save bills to downloads folder
        output_file = os.path.join(downloads_dir, f"raw-{session_id}-bills.json")
        with open(output_file, "w") as bills_file:
            json.dump(bills_data, bills_file, indent=4)
        print(f"Bills data saved to '{output_file}'.")
    else:
        print("No data to save.")
