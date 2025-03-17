# Montana Legislative Interface
Program for grabbing data from Montana Legislature's new bill tracker and processing it for use in [MTFP](https://montanafreepress.org/)'s [Capitol Tracker](https://github.com/mtfreepress/capitol-tracker-2025)

## How do I run it?
- Runs via GitHub Actions automatically on a timer to keep up with legislative session changes
- Can be run manually via execute.sh shell script

## What it does
- Takes in Bill data
- Downloads PDF vote sheets
    - Does caching to avoid downloading same PDFs each time it runs
- Parses PDF votes into json 

Forcing GHA to run with this change