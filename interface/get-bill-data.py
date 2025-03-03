import os
import json
import requests
import sys
import time

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

def fetch_bills(session_id, max_retries=5):
    bills_url = "https://api.legmt.gov/bills/v1/bills/search?includeCounts=true&sort=billType.code,desc&sort=billNumber,asc&sort=draft.draftNumber,asc&limit=9999&offset=0"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://bills.legmt.gov",
        "Referer": "https://bills.legmt.gov/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }

    # Wrap session_id in a list
    payload = {"sessionIds": [session_id]}
    
    # Try preflight first (CORS handling)
    try:
        print("Performing preflight OPTIONS request...")
        options_headers = {
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            "Origin": "https://bills.legmt.gov",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        preflight = requests.options(bills_url, headers=options_headers, timeout=10)
        print(f"Preflight status: {preflight.status_code}")
    except Exception as e:
        print(f"Preflight request failed (this is often normal): {e}")
    
    # Try API request with retries
    for attempt in range(1, max_retries + 1):
        try:
            print(f"API Request attempt {attempt}/{max_retries}")
            
            # Try adding more browser-like headers to bypass WAF
            if attempt > 1:
                headers.update({
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "sec-ch-ua": '"Google Chrome";v="133", "Chromium";v="133", "Not-A.Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"macOS"'
                })
            
            response = requests.post(bills_url, json=payload, headers=headers, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            
            # Always save the full response for inspection
            error_log_dir = os.path.join(os.path.dirname(__file__), "error_logs")
            os.makedirs(error_log_dir, exist_ok=True)
            error_log_path = os.path.join(error_log_dir, f"api_response_{attempt}.html")
            
            with open(error_log_path, 'w') as f:
                f.write(response.text)
            print(f"Full response saved to {error_log_path}")
            
            # Check if response is HTML instead of JSON
            if "text/html" in response.headers.get('Content-Type', ''):
                print(f"WARNING: Received HTML instead of JSON - see {error_log_path}")
                # Continue to next attempt
            elif response.status_code == 200 and response.text.strip():
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
            
            if attempt < max_retries:
                delay = 2 ** attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            if attempt < max_retries:
                delay = 2 ** attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    # If we get here, all attempts failed
    print("All API attempts failed")
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




# TODO: This is the old version keeping it just in case
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
