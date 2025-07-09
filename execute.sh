#!/bin/bash

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

# measure time taken for a command
measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

# get bill data json
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

# get ammendments
measure_time python ./interface/get-amendments.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"

# compress fiscal notes:
measure_time python interface/compress-pdfs.py interface/downloads/fiscal-note-pdfs-$sessionId

# compress bill text PDFs:
measure_time python interface/compress-pdfs.py interface/downloads/bill-text-pdfs-$sessionId

# compress veto-lettrs:
measure_time python interface/compress-pdfs.py interface/downloads/veto-letter-pdfs-$sessionId

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
# measure_time python ./process/merge-actions.py $sessionId

# Process committees data
measure_time python ./process/process-committees.py $sessionId

# parse vote jsons:
# measure_time python ./process/process-vote-json.py $sessionId

# process bill json into format we need
measure_time python ./process/process-bills.py $sessionId