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


# get bill data json
python ./interface/get-bill-data.py $sessionId

# get legislators
python ./interface/get-legislators.py

# generate list of bills for input into other scripts
python ./interface/generate-bill-list.py $sessionId

# get vote data:
python ./interface/get-votes-json.py

#TODO: logic for `if sessionOrdinal is <20251, use this else use get-votes-json.py`
# download PDFs - only needed for sessions prior to 2025:
# python ./interface/get-pdf-votesheets.py --sessionId "$sessionId" --legislatureOrdinal "$legislatureOrdinal" --sessionOrdinal "$sessionOrdinal"

# parse vote counts from PDFs
python ./process/process-vote-pdfs.py $sessionId

# process bill json into format we need
python ./process/process-bills.py $sessionId

# process bill actions
python ./process/process-actions.py $sessionId