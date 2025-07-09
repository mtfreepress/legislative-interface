#!/bin/bash

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
measure_time python interface/get-bill-text-pdf.py $sessionId $legislatureOrdinal $sessionOrdinal