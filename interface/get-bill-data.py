import os
import json
import requests
import sys
import random
import time

# Define constants
max_retries = 5
retry_delay_base = 2

# NOTE: 2023 and older use this endpoint

# 2023 API URL and headers
# def fetch_bills(session_id):
# bills_url = "https://api.legmt.gov/archive/v1/bills/search?limit=9999&offset=0"
# headers = {
#     "Accept": "application/json, text/plain, */*",
#     "Content-Type": "application/json",
#     "Origin": "https://bills.legmt.gov",
#     "Referer": "https://bills.legmt.gov/",
# }

# --- 2025 API is different --- 

def fetch_bills(session_id):
    bills_url = "https://api.legmt.gov/bills/v1/bills/search?includeCounts=true&sort=billType.code,desc&sort=billNumber,asc&sort=draft.draftNumber,asc&limit=9999&offset=0"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://bills.legmt.gov",
        "Referer": "https://bills.legmt.gov/",
    }

    # Use a session for better connection handling
    session = requests.Session()
    
    # Wrap session_id in a list
    payload = {"sessionIds": [session_id]}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries} to fetch bills data...")
            
            # Add a small random delay to avoid synchronized requests
            if attempt > 1:
                jitter = random.uniform(0.5, 1.5)
                delay = retry_delay_base * (2 ** (attempt - 1)) * jitter
                print(f"Waiting {delay:.2f} seconds before retry...")
                time.sleep(delay)
            
            # First try with OPTIONS to simulate browser behavior
            if attempt == 1:
                print("Performing OPTIONS request first...")
                options_headers = {
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Access-Control-Request-Headers": "content-type",
                    "Access-Control-Request-Method": "POST",
                    "Connection": "keep-alive",
                    "Origin": "https://bills.legmt.gov",
                    "Referer": "https://bills.legmt.gov/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                }
                session.options(bills_url, headers=options_headers, timeout=30)
            
            # Then perform the actual POST request
            response = session.post(bills_url, json=payload, headers=headers, timeout=30)
            
            print(f"HTTP Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Length: {len(response.text)} characters")
            
            if response.text:
                preview = response.text[:100] + ("..." if len(response.text) > 100 else "")
                print(f"Response Preview: {preview}")
            else:
                print("Response body is empty!")
            
            if response.status_code == 200:
                if not response.text:
                    print("Warning: Received empty response body with 200 status code")
                    continue

                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    continue
            else:
                print(f"Failed with status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Request exception: {e}")
        
        print(f"Attempt {attempt} failed, will retry...")
    
    print("All attempts failed")
    return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get-bill-data.py <session_id>")
        sys.exit(1)

    # Get session_id from command-line arguments
    session_id = int(sys.argv[1])

    # Create downloads directory if it doesn't exist
    downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    # Fetch bills data
    bills_data = fetch_bills(session_id)
    if bills_data is not None:
        # Save bills to downloads folder
        output_file = os.path.join(downloads_dir, f"raw-{session_id}-bills.json")
        with open(output_file, "w") as bills_file:
            json.dump(bills_data, bills_file, indent=4)
        print(f"Bills data saved to '{output_file}'.")
    else:
        print("No data to save.")

# TODO: Remove or revert to this old version

# def fetch_bills(session_id):
#     bills_url = "https://api.legmt.gov/bills/v1/bills/search?includeCounts=true&sort=billType.code,desc&sort=billNumber,asc&sort=draft.draftNumber,asc&limit=9999&offset=0"
#     headers = {
#         "Accept": "application/json, text/plain, */*",
#         "Content-Type": "application/json",
#         "Origin": "https://bills.legmt.gov",
#         "Referer": "https://bills.legmt.gov/",
#     }

#     # Wrap session_id in a list, use format that for some reason changed
#     payload = {"sessionIds": [session_id]}

#     response = requests.post(bills_url, json=payload, headers=headers)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         print(f"Failed to fetch bills. HTTP Status Code: {response.status_code}")
#         print(f"Response: {response.text}")
#         return None

# if __name__ == "__main__":
#     if len(sys.argv) != 2:
#         print("Usage: python get-bill-data.py <session_id>")
#         sys.exit(1)

#     # Get session_id from command-line arguments
#     session_id = int(sys.argv[1])

#     # Create downloads directory if it doesn't exist
#     downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
#     os.makedirs(downloads_dir, exist_ok=True)

#     # Fetch bills data
#     bills_data = fetch_bills(session_id)
#     if bills_data is not None:
#         # Save bills to downloads folder
#         output_file = os.path.join(downloads_dir, f"raw-{session_id}-bills.json")
#         with open(output_file, "w") as bills_file:
#             json.dump(bills_data, bills_file, indent=4)
#         print(f"Bills data saved to '{output_file}'.")
#     else:
#         print("No data to save.")
