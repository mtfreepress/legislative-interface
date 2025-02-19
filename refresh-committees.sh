#!/bin/bash

measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

sessionId=2 
sessionOrdinal=20251 
legislatureOrdinal=69
year=2025

# get all committees
measure_time python ./interface get-all-committees.py $sessionId

# get legislators json
measure_time python ./interface/get-legislators.py

# process legislators & committees in to a csv
measure_time python ./interface/process-legislators-committees.py