#!/bin/bash

set -e

# 2023 arguments 
# 2023 and older requires changing the api call in get-bill-data
# Commented out at the top of the file
# sessionId=20231
# sessionOrdinal=20251
# legislatureOrdinal=69

# 2025 arguments
sessionId=2 
sessionOrdinal=20251 
legislatureOrdinal=69

# Function to log errors
log_error() {
    echo "Error on line $1"
    timestamp=$(date -u)
    ip_address=$(curl -s ifconfig.me)
    echo "${timestamp} - ${ip_address} - Error on line $1" >> failed-runs.txt
    cat failed-runs.txt
    git config user.name "Automated"
    git config user.email "actions@users.noreply.github.com"
    git add failed-runs.txt
    git commit -m "Failed run: ${timestamp}" || exit 0
    git push origin $TEST_BRANCH
}

# Trap errors and log them
trap 'log_error $LINENO' ERR

# measure time taken for a command
measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

# Run the Python script and capture the output
output=$(python ./interface/get-bill-data.py $sessionId 2>&1)

# Check if the output contains JSONDecodeError
if echo "$output" | grep -q 'json.decoder.JSONDecodeError'; then
  echo "Error detected: JSONDecodeError"
  # Get the current date/time and IP address
  timestamp=$(date -u)
  ip_address=$(curl -s ifconfig.me)
  # Write to failed-runs.txt
  echo "${timestamp} - ${ip_address}" >> failed-runs.txt
  cat failed-runs.txt
  # Commit and push the changes
  git config user.name "Automated"
  git config user.email "actions@users.noreply.github.com"
  git add failed-runs.txt
  git commit -m "Failed run: ${timestamp}" || exit 0
  git push origin $TEST_BRANCH
  exit 1
fi

# If no error, continue with the rest of the script
measure_time python ./interface/get-bill-data.py $sessionId

# split into separate files for processing
measure_time python ./interface/split-bills.py $sessionId

# match votes with actions:

# get legislators
measure_time python ./interface/get-legislators.py

# get all committees 
measure_time python ./interface/get-all-committees.py $sessionId

# get agencies 
measure_time python ./interface/get-agencies.py $sessionId

# generate list of bills for input into other scripts
measure_time python ./interface/generate-bill-list.py $sessionId

# get legal notices
measure_time python ./interface/get-legal-review-notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"

# get fiscal notices
measure_time python ./interface/get-fiscal-review-notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"

# get amendments
measure_time python ./interface/get-amendments.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"

# compress fiscal notes:
measure_time python interface/compress-pdfs.py interface/downloads/fiscal-note-pdfs-$sessionId

### These two don't seem worth doing. Take awhile and save less than 3MB
# compress legal notes:
measure_time python interface/compress-pdfs.py interface/downloads/legal-note-pdfs-$sessionId
# compress amendments:
# measure_time python interface/compress-pdfs.py interface/downloads/amendment-pdfs-$sessionId

# get committee hearings data
measure_time python ./interface/get-bill-hearings.py $sessionId

# get vote data:
measure_time python ./interface/get-votes-json.py $sessionId

# executive actions data
measure_time python ./interface/get-executive-actions-json.py $sessionId

# get committees by id
measure_time python ./interface/get-committees.py $sessionId

# match some votes:
measure_time python ./interface/match-votes-actions.py $sessionId

#TODO: logic for `if sessionOrdinal is <20251, use this else use get-votes-json.py`
# download PDFs - only needed for sessions prior to 2025:
# measure_time python ./interface/get-pdf-votesheets.py --sessionId "$sessionId" --legislatureOrdinal "$legislatureOrdinal" --sessionOrdinal "$sessionOrdinal"

# parse vote counts from PDFs - pre-2025 only
# measure_time python ./process/process-vote-pdfs.py $sessionId

# merge actions and votes:
measure_time python ./process/merge-actions.py $sessionId

# parse vote jsons:
# measure_time python ./process/process-vote-json.py $sessionId

# process bill json into format we need
measure_time python ./process/process-bills.py $sessionId