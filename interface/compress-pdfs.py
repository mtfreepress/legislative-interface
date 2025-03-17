import os
import json
import subprocess
import hashlib
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

def load_tracking_data(tracking_file):
    """Load previously compressed files data"""
    if os.path.exists(tracking_file):
        with open(tracking_file, 'r') as f:
            return json.load(f)
    return {}

def save_tracking_data(data, tracking_file):
    """Save compressed files tracking data"""
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=2)

def get_file_hash(file_path):
    """Get a hash of file contents for change detection"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def needs_compression(file_path, tracking_data):
    """Check if file needs compression based on content hash"""
    if not os.path.exists(file_path):
        return False
        
    current_hash = get_file_hash(file_path)
    
    if file_path in tracking_data:
        # if hash matches, file hasn't changed
        if tracking_data[file_path]["hash"] == current_hash:
            return False
    
    return True

def load_update_files(update_files):
    """Load file paths from update JSON files"""
    update_paths = set()
    
    for update_file in update_files:
        if os.path.exists(update_file):
            try:
                with open(update_file, 'r') as f:
                    updates = json.load(f)
                    
                for update in updates:
                    if "billType" in update and "billNumber" in update:
                        # extract bill info
                        bill_type = update["billType"]
                        bill_number = update["billNumber"]
                        
                        # add potential paths to the set
                        update_paths.add((bill_type, bill_number))
                        
                print(f"Loaded {len(updates)} updates from {update_file}")
            except Exception as e:
                print(f"Error loading update file {update_file}: {e}")
    
    return update_paths

def should_process_file(file_path, update_paths, force_all):
    """Check if file should be processed based on update paths"""
    if force_all:
        return True
        
    if not update_paths:
        return True
        

    parts = file_path.split(os.sep)
    for i, part in enumerate(parts):
        if '-' in part and i < len(parts) - 1:
            try:
                bill_parts = part.split('-')
                if len(bill_parts) == 2:
                    bill_type = bill_parts[0]
                    bill_number = int(bill_parts[1])
                    if (bill_type, bill_number) in update_paths:
                        return True
            except (ValueError, IndexError):
                pass
    
    return False

def compress_pdf(args):
    """Compress a single PDF file"""
    # update to unpack all arguments
    file_path, tracking_data, quality, dryrun, output_dir, directory, update_paths, force_all = args
    
    # skip files not in update paths (if filtering is active)
    if not should_process_file(file_path, update_paths, force_all):
        return False, file_path, "Not in update list"
    
    if not needs_compression(file_path, tracking_data):
        return False, file_path, "Unchanged"
        
    # determine output path - either replace original or create in output dir
    if output_dir:
        rel_path = os.path.relpath(file_path, directory)
        new_output_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(new_output_path), exist_ok=True)
        temp_output = new_output_path
    else:
        # Original behavior - replace in place
        temp_output = f"{file_path}.compressed.pdf"
    
    try:
        # Skip actual compression in dry run mode
        if dryrun:
            print(f"[DRY RUN] Would compress: {file_path}")
            return False, file_path, "Dry Run"
            
        # Run ghostscript to compress
        result = subprocess.run([
            'gs', 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS=/{quality}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={temp_output}',
            file_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, file_path, f"Error: {result.stderr}"
            
        # check if compression was successful and worthwhile
        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(temp_output)
        
        if compressed_size < original_size * 0.95:  # file must be at least 5% smaller or it is skipped
            # if not using output directory, replace original
            if not output_dir:
                os.replace(temp_output, file_path)
            
            # get hash
            compressed_hash = get_file_hash(temp_output if output_dir else file_path)
            
            # update tracking data
            tracking_data[file_path] = {
                "hash": compressed_hash,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compressed_size / original_size,
                "last_compressed": datetime.now().isoformat(),
                "output_path": temp_output if output_dir else file_path
            }
            
            return True, file_path, {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "savings": original_size - compressed_size,
                "percent": (1 - compressed_size/original_size) * 100,
                "output_path": temp_output if output_dir else file_path
            }
        else:
            # compression not worth it
            if not output_dir:  # only delete temp file if size change isn't worth it
                os.remove(temp_output)
            
            # track the file so we don't try again
            tracking_data[file_path] = {
                "hash": get_file_hash(file_path),
                "skipped": True,
                "reason": "minimal_savings",
                "last_checked": datetime.now().isoformat()
            }
            
            return False, file_path, "Minimal savings"
            
    except Exception as e:
        if os.path.exists(temp_output) and not output_dir:
            os.remove(temp_output)
        return False, file_path, f"Exception: {str(e)}"

def find_pdf_files(directory):
    """Find all PDF files in the directory (recursive)"""
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

def compress_pdf_directory(directory, tracking_file, quality='ebook', workers=None, 
                          dryrun=False, output_dir=None, update_files=None, force_all=False):
    """Compress all PDF files in the directory using multiple processes"""
    # default workers to CPU count
    if workers is None:
        workers = os.cpu_count()
        print ("We have this many workers")
        print(workers)
    
    # create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        # print(f"Compressed files will be saved to: {output_dir}")
    
    # load tracking data
    tracking_data = load_tracking_data(tracking_file)
    
    # load update files if specified
    update_paths = set()
    if update_files and not force_all:
        update_paths = load_update_files(update_files)

    all_pdf_files = find_pdf_files(directory)
    
    if not all_pdf_files:
        return

    
    # Prepare arguments for the worker function
    work_args = [(pdf_file, tracking_data, quality, dryrun, output_dir, directory, update_paths, force_all) 
                for pdf_file in all_pdf_files]
    
    # Track results
    compressed_count = 0
    unchanged_count = 0
    skipped_count = 0
    total_savings = 0
    
    # Process files in parallel
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(compress_pdf, args) for args in work_args]
        
        # Process results as they complete
        for future in as_completed(futures):
            success, file_path, result = future.result()
            
            if success:
                compressed_count += 1
                savings = result["savings"]
                total_savings += savings
            else:
                pass
    # only save tracking data if not in dry run mode
    if not dryrun:
        save_tracking_data(tracking_data, tracking_file)
    
    # print summary
    print(f"\nCompression Summary:")
    print(f"- Total PDFs found: {len(all_pdf_files)}")
    print(f"- Compressed: {compressed_count} files")
    print(f"- Unchanged: {unchanged_count} files")
    print(f"- Not in update list: {skipped_count} files")
    print(f"- Other skips: {len(all_pdf_files) - compressed_count - unchanged_count - skipped_count} files")
    print(f"- Total savings: {total_savings/1024/1024:.2f} MB")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress PDF files using Ghostscript")
    parser.add_argument("directory", help="Directory containing PDF files to compress")
    parser.add_argument("--tracking-file", default="compressed_files.json", 
                     help="JSON file to track compressed files (default: compressed_files.json)")
    parser.add_argument("--quality", choices=['screen', 'ebook', 'printer', 'prepress'], default='ebook',
                     help="Compression quality level (default: ebook)")
    parser.add_argument("--workers", type=int, default=None,
                     help="Number of worker processes (default: number of CPU cores)")
    parser.add_argument("--dry-run", action="store_true",
                     help="Dry run - don't actually compress files")
    parser.add_argument("--output-dir", 
                     help="Output directory for compressed files (default: replace originals)")
    parser.add_argument("--update-files", nargs='+',
                     help="JSON files containing updates to process (only process bills in these files)")
    parser.add_argument("--force-all", action="store_true",
                     help="Force processing all files, ignoring update files")
    
    args = parser.parse_args()
    
    compress_pdf_directory(args.directory, args.tracking_file, 
                         args.quality, args.workers, args.dry_run, args.output_dir,
                         args.update_files, args.force_all)