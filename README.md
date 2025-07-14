# Montana Legislative Interface

This project is a from-scratch writing of a data pipeline by [Jacob Olness](https://github.com/jolness1) for the new [MT Legislative Bill Explorer](https://bills.legmt.gov/) that scrapes, processes, and organizes data from the Montana Legislature's bill tracker for use in [Montana Free Press](https://montanafreepress.org/)' [Capitol Tracker](https://github.com/mtfreepress/capitol-tracker-2025). It automates downloading, parsing, and transforming legislative data including bills, committees, votes, amendments, and PDFs to work with the Capitol Tracker data expectations formed by the state's decades-old previous bill tracker. Montana Free press is a 501(c)(3) nonprofit newsroom that aims to provide Montanans with in-depth, nonpartisan news coverage. 

A live version of the 2025 tracker can be found at [https://projects.montanafreepress.org/capitol-tracker-2025/](https://projects.montanafreepress.org/capitol-tracker-2025/)

---
## Considerations:

Pipeline runs automatically via GitHub Actions set up in [`.github/workflows/data.yml`](.github/workflows/data.yml). There are cron jobs set up for active hours during the session and a reduced rate of 1x/hr for after Sine Die. Comment one out and uncomment the other to switch between them. 

Wherever possible caching has been implemented to minimize load on the state's servers while helping to provide a service to the public in compliance with [Montana Constitution Article II, § 9's "Right To Know"](https://archive.legmt.gov/bills/mca/title_0000/article_0020/part_0010/section_0090/0000-0020-0010-0090.html) provision. For example — 
1. PDFs are only downloaded if the latest version isn't stored locally
2. The GitHub Actions pipeline runs only during the day 

---

## Quick Start

### 1. Fork repository something like:

``` 
legislative-interface-{year}
```

### 2. Clone and Setup 
(modify this to match the forked repo url)

```bash
git clone https://github.com/mtfreepress/legislative-interface.git 
cd legislative-interface
```

### 3. Create Python Virtual Environment & Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Make `execute.sh` executable
```bash
chmod +x ./execute.sh
```

### 5. Run the Full Pipeline

```bash
./execute.sh
```

---

## How the Pipeline Works

The [`execute.sh`](execute.sh) script runs the entire data collection and processing pipeline in order. Here's what each step does:

### Phase 1: Initial Data Collection

| Script | Purpose |
|--------|---------|
| [`interface/get-bill-data.py`](interface/get-bill-data.py) | Downloads raw bill data from the Montana Legislature API |
| [`interface/split-bills.py`](interface/split-bills.py) | Splits the large bill JSON into individual files for easier processing |
| [`interface/get-legislators.py`](interface/get-legislators.py) | Downloads legislator data and roster information |
| [`interface/get-all-committees.py`](interface/get-all-committees.py) | Downloads all committee data (standing and non-standing) |
| [`interface/get-agencies.py`](interface/get-agencies.py) | Downloads state agency data |
| [`interface/generate-bill-list.py`](interface/generate-bill-list.py) | Creates a list of bills for input into other scripts |

### Phase 2: Document Downloads

| Script | Purpose |
|--------|---------|
| [`interface/get-legal-review-notes.py`](interface/get-legal-review-notes.py) | Downloads legal review notes and veto letters for bills |
| [`interface/get-fiscal-review-notes.py`](interface/get-fiscal-review-notes.py) | Downloads fiscal notes and rebuttals for bills |
| [`interface/get-bill-text-pdf.py`](interface/get-bill-text-pdf.py) | Downloads bill text PDFs |
| [`interface/get-amendments.py`](interface/get-amendments.py) | Downloads bill amendments and amendment PDFs |

### Phase 3: PDF Compression

| Script | Purpose |
|--------|---------|
| [`interface/compress-pdfs.py`](interface/compress-pdfs.py) | Compresses downloaded PDFs to save space |
###### Invoked with and argument of the pdf directory needing compression:
```
python interface/compress-pdfs.py {path/to/pdf-directory}
```

### Phase 4: Vote & Action Data

| Script | Purpose |
|--------|---------|
| [`interface/get-bill-hearings.py`](interface/get-bill-hearings.py) | Downloads committee hearing data for bills |
| [`interface/get-votes-json.py`](interface/get-votes-json.py) | Downloads vote data for bills (2025+ sessions) |
| [`interface/get-executive-actions-json.py`](interface/get-executive-actions-json.py) | Downloads executive actions data |
| [`interface/get-committees.py`](interface/get-committees.py) | Downloads committee data by ID |
| [`interface/match-votes-actions.py`](interface/match-votes-actions.py) | Matches votes with bill actions for analysis |

### Phase 5: Data Processing

| Script | Purpose |
|--------|---------|
| [`process/process-committees.py`](process/process-committees.py) | Processes committee data, applies whitelist filtering, generates committee statistics |
| [`process/process-bills.py`](process/process-bills.py) | Processes bill data into the final format needed for downstream use |

### Legacy Scripts (Pre-2025 Sessions) - 
#### Largely deprecated as of July 2025 — appears that the state has manually moved at least vote *counts* over to the new json system dating back to 1999. 

| Script | Purpose |
|--------|---------|
| [`interface/get-pdf-votesheets.py`](interface/get-pdf-votesheets.py) | Downloads vote sheet PDFs (pre-2025 sessions only) |
| [`process/process-vote-pdfs.py`](process/process-vote-pdfs.py) | Parses vote PDFs into JSON (pre-2025 sessions only) |

## Scripts that have been superseded by `./interface/match-votes-actions`

| Script | Purpose |
|--------|---------|
| [`process/merge-actions.py`](process/merge-actions.py) | Merges actions and votes data |

---

## Key Configuration Files

- **Session Configuration**: Edit the variables at the top of [`execute.sh`](execute.sh) for different legislative sessions
- **Committee Filtering**: Edit `COMMITTEE_WHITELIST` in [`process/process-committees.py`](process/process-committees.py) to control which committees are processed
- **Committee Display Names**: [`interface/downloads/committee_mapping.csv`](interface/downloads/committee_mapping.csv) maps committee keys to display names

---

## File Structure

```
legislative-interface/
├── execute.sh               # Main pipeline script
├── interface/               # Data collection scripts
│   ├── downloads/           # Raw downloaded data
│   ├── get-*.py             # Data download scripts
│   ├── /raw-data-dirs       # Data output with more than 1 output file (ie split bills/votes etc)
│   └── *.json               # Output files (with only 1 output like the entire json of all bills)
├── process/                 # Data processing scripts
│   ├── cleaned/             # Processed output data
│   └── process-*.py         # Data transformation scripts
└── requirements.txt         # Python dependencies
```

---

## Session Configuration

For new legislative sessions, update these variables in [`execute.sh`](execute.sh):

```bash
sessionId=2                   # Session identifier for 2025 for some reason
sessionOrdinal=20251          # Session ordinal number  (special session would be 20252)
legislatureOrdinal=69         # Legislature number (2027 will be Montana's 70th legislative session)
```

---

## Troubleshooting

### Common Issues

1. **Missing committees in output**: Check the `COMMITTEE_WHITELIST` in [`process/process-committees.py`](process/process-committees.py) and ensure filenames match expected keys.

2. **API rate limiting**: The scripts use connection limits and user-agent headers to be respectful of the state's API.

3. **File path issues**: All scripts use relative paths from their directory location to work with the [`execute.sh`](execute.sh) runner.

### Dependencies

- **Python 3.13+**
- **aiohttp**: For async HTTP requests
- **requests**: For synchronous HTTP requests
- **PyPDF2** or similar: For PDF processing (if using legacy vote parsing—should be unneccesary but just in case™)

---

## Development Notes

- The Montana Legislature's API and website structure can change between sessions
- Scripts are designed to be modular - you can run individual components if needed
- The pipeline includes extensive error handling and file existence checks
- PDF downloads include caching to avoid re-downloading existing files
- All scripts log their progress and execution time

---

## Automation

- Designed to run via GitHub Actions on a schedule
- Can be run manually with `bash execute.sh`
- Includes timing measurements for performance monitoring

---

## License

"New" BSD License (aka "3-clause"). See [LICENSE](LICENSE) for details.

---

## Contributing

When adding new scripts or modifying existing ones:

1. Follow the existing naming convention (`get-*.py` for downloads, `process-*.py` for processing)
2. Add the script to [`execute.sh`](execute.sh) in the appropriate phase
3. Update this README with a description of what the script does
4. Use relative paths and the established directory structure

---

**For the next legislative session (2027)**: 
1) __After forking__ delete the old data from last session
2) Update session variables 
3) Check API endpoints for functionality
4) Change the URL for Capitol Tracker's legislators [`interface/get-legislators.py`](interface/get-legislators.py) (There is a TODO right above the line) or change it to manage those annotations in this repo instead. 
