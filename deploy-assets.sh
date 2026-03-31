#!/bin/bash
# deploy-assets.sh
# Uploads PDFs and document index to S3, separate from the Next.js build.
# Uses --size-only so only genuinely changed files get uploaded.
# This replaces the old approach of bundling PDFs in the Next.js public/ dir.

set -e

S3_BUCKET="s3://projects.montanafreepress.org/capitol-tracker-2025"
CLOUDFRONT_DISTRIBUTION_ID="E1G7ISX2SZFY34"
SESSION_ID="${1:-2}"
DOWNLOADS_DIR="interface/downloads"

measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

echo "=== Deploying static assets to S3 ==="
echo "Session ID: $SESSION_ID"
echo "Downloads dir: $DOWNLOADS_DIR"

# Sync bill text PDFs
echo "Syncing bill text PDFs..."
measure_time aws s3 sync "$DOWNLOADS_DIR/bill-text-pdfs-$SESSION_ID" "$S3_BUCKET/bill-texts" \
    --size-only \
    --no-progress

# Sync amendment PDFs
echo "Syncing amendment PDFs..."
measure_time aws s3 sync "$DOWNLOADS_DIR/amendment-pdfs-$SESSION_ID" "$S3_BUCKET/amendments" \
    --size-only \
    --no-progress

# Sync fiscal note PDFs
echo "Syncing fiscal note PDFs..."
measure_time aws s3 sync "$DOWNLOADS_DIR/fiscal-note-pdfs-$SESSION_ID" "$S3_BUCKET/fiscal-notes" \
    --size-only \
    --no-progress

# Sync legal note PDFs
echo "Syncing legal note PDFs..."
measure_time aws s3 sync "$DOWNLOADS_DIR/legal-note-pdfs-$SESSION_ID" "$S3_BUCKET/legal-notes" \
    --size-only \
    --no-progress

# Sync veto letter PDFs
echo "Syncing veto letter PDFs..."
if [ -d "$DOWNLOADS_DIR/veto-letter-pdfs-$SESSION_ID" ]; then
    measure_time aws s3 sync "$DOWNLOADS_DIR/veto-letter-pdfs-$SESSION_ID" "$S3_BUCKET/veto-letters" \
        --size-only \
        --no-progress
else
    echo "No veto letter directory found, skipping."
fi

# Upload document index and bills-with-amendments list
echo "Uploading document index files..."
if [ -f "output/document-index.json" ]; then
    aws s3 cp "output/document-index.json" "$S3_BUCKET/document-index.json"
fi
if [ -f "output/bills-with-amendments.txt" ]; then
    aws s3 cp "output/bills-with-amendments.txt" "$S3_BUCKET/bills-with-amendments.txt"
fi

# Invalidate only the asset paths on CloudFront (not the whole site)
echo "Invalidating CloudFront cache for assets..."
aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/capitol-tracker-2025/document-index.json" "/capitol-tracker-2025/bills-with-amendments.txt"

echo "=== Asset deployment complete ==="
