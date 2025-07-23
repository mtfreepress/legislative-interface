import os
import re
from pypdf import PdfReader
import json

# NOTE: This is not needed each run

class PDFNameExtractor:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the script

    def extract_names_from_pdf(self, bill_type, bill_number, session_id, unique_names):
        # extract names and add to set
        bill_dir = f"{bill_type}{bill_number}"
        pdf_dir = os.path.join(self.base_path, '..', 'vote_pdfs_fast', bill_dir)  # Path relative to the script

# NOTE: Disabled for prod, too verbose
        # if not os.path.exists(pdf_dir):
            # return {"error": f"Directory not found: {pdf_dir}"}

        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        if not pdf_files:
            return {"error": f"No PDFs found in directory: {pdf_dir}"}

        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            print(f"Processing PDF: {pdf_path}")

            try:
                with open(pdf_path, 'rb') as f:
                    pdf = PdfReader(f)
                    text = pdf.pages[0].extract_text()

                    # Parse the vote section using a regular expression
                    vote_pattern = re.compile(r'^([YN])([A-Za-z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zAZ\'\-]+)*)', re.MULTILINE)
                    
                    for match in vote_pattern.finditer(text):
                        # Skip if the match starts with 'EAS' or contains non-name characters
                        name = match.group(2).replace('; by proxy', '').strip()
                        if name == 'EAS' or not all(c.isalpha() or c.isspace() or c in "'-" for c in name):
                            continue
                        
                        # Add name to the set (ensures uniqueness)
                        unique_names.add(name)

            except Exception as e:
                print(f"Error processing PDF {pdf_file}: {str(e)}")

    def save_unique_names(self, unique_names):
       # save unique names to json
        # Sort names alphabetically
        sorted_names = sorted(unique_names)

        # Get the directory where the script is located
        output_dir = self.base_path

        # Saving as JSON
        output_file_json = os.path.join(output_dir, "unique-names.json")
        with open(output_file_json, 'w') as f:
            json.dump(sorted_names, f, indent=4)
            # print(f"Saved results to {output_file_json}")

        # Saving as text
        output_file_txt = os.path.join(output_dir, "unique-names.txt")
        with open(output_file_txt, 'w') as f:
            for name in sorted_names:
                f.write(f"{name}\n")
            # print(f"Saved results to {output_file_txt}")

        # Print the count of unique names
        print(f"Total unique names: {len(unique_names)}")

def load_bill_list(file_path):
    """
    Load the list of bills from a JSON file.
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading bill list: {e}")
        return []

# Standalone usage example:
if __name__ == "__main__":
    sessionId = 20231
    bill_list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../interface/list-bills-{sessionId}.json")  # Absolute path to the bill list file

    extractor = PDFNameExtractor()

    # Load bills
    bills = load_bill_list(bill_list_file)

    # Set to hold unique names
    unique_names = set()

    # Process each bill and extract names
    for bill in bills:
        bill_type = bill.get("billType")
        bill_number = bill.get("billNumber")
        if bill_type and bill_number:
            extractor.extract_names_from_pdf(bill_type, bill_number, sessionId, unique_names)

    # Save unique names to a file and print the count
    extractor.save_unique_names(unique_names)
