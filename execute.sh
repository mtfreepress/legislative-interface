# TODO: Maybe modify these to take in an argument for `sessionId`

# get bill data json
/interface/get-bill-data.py

# get legislators
/interface/get-legislators.py

# generate list of bills for input into other scripts
/interface/generate-bill-list.py

# May or may not be needed, currently it has data that the get-bill-data doesn't
interface/get-expanded-bill-data.py

# download PDFs:
/interface/get-pdf-votesheets.py

# parse vote counts from PDFs
/process/process-vote-pdfs.py

# process bill json into format we need
/process/process-bills.py