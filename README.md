# Montana Legislative Interface
Program for grabbing data from Montana Legislature's new bill tracker and processing it for use in [MTFP](https://montanafreepress.org/)'s [Capitol Tracker](https://github.com/mtfreepress/capitol-tracker-2025)

## How do I run it?
- Runs via GitHub Actions automatically on a timer to keep up with legislative session changes
- #### note: run `chmod +x ./execute.sh` and `chmod +x .refresh-committees.sh` to make them executable (only required first time after downloading, will remain executable)
- Can be run manually via `execute.sh` shell script
- `refresh-committees.sh` is run as needed for committee updating (usually only at start of session)

## What it does
- Takes in Bill data
- Downloads PDF vote sheets
    - Does caching to avoid downloading same PDFs each time it runs
- Parses PDF votes into json 

