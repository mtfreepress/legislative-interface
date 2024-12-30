# legislative-interface
Program for grabbing data from Montana Legislature's new bill tracker for use in [MTFP](https://montanafreepress.org/)'s [Capitol Tracker](https://github.com/mtfreepress/capitol-tracker-2025)

- Runs via GitHub Actions automatically

- Takes in Bill data
- Downloads PDF vote sheets
    - Does caching to avoid downloading same PDFs each time it runs
- Parses PDF votes into json 

