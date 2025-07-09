import os
import re
from pypdf import PdfReader
import json
import sys

# Only for sessions prior to 2025 where PDF vote sheets are the 
# TODO: Fix the "A IR" bug
# TODO: Map "Mr. Speaker" to name of speaker (maybe do that in front end?)

class PDFVoteParser:
    def __init__(self):
        """
        Initialize the parser with a base directory path relative to the script location.
        """
        self.base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../inputs/")

    def parse_pdf_vote(self, bill_type, bill_number, session_id):
        """
        Parses all PDFs found for the given bill type and number.
        Outputs the parsed data in JSON format for each PDF.
        """
        bill_dir = f"{bill_type}{bill_number}"
        pdf_dir = os.path.join(self.base_path, 'vote_pdfs', bill_dir)

        # Check if the directory exists
        if not os.path.exists(pdf_dir):
            print(f"Warning: Directory not found: {pdf_dir}")
            return []  # Return an empty list if the directory doesn't exist

        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        if not pdf_files:
            print(f"Warning: No PDFs found in directory: {pdf_dir}")
            return []  # Return an empty list if no PDFs are found

        all_data = []

        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            print(f"Processing PDF: {pdf_path}")

            try:
                with open(pdf_path, 'rb') as f:
                    pdf = PdfReader(f)
                    text = pdf.pages[0].extract_text()
                    # DEBUG:
                    # print(f"Extracted text for {pdf_file}:")
                    # print(text)

# comittee bills –– format of `HB0001APH230105.pdf`
                    if pdf_file.startswith(bill_type):
                        # date
                        date_match = re.search(r'(?:DATE:\s*)?(\bJanuary|\bFebruary|\bMarch|\bApril|\bMay|\bJune|\bJuly|\bAugust|\bSeptember|\bOctober|\bNovember|\bDecember)\s+\d{1,2},\s+\d{4}', text)
                        date = date_match.group(0).strip() if date_match else "Date not found"

                        # motion description (now captures title + name)
                        motion_match = re.search(r'([A-Za-z]+\.?\s+[A-Za-z\s]+)\s+made a Motion that\s+[^\n]+', text)
                        description = motion_match.group(0).strip() if motion_match else "Description not found"

                        # vote totals
                        totals_patterns = [
                            r'YEAS\s+\u2013\s+(\d+)\s+NAYS\s+-\s+(\d+)',
                            r'YEAS\s+-\s+(\d+)\s+NAYS\s+-\s+(\d+)',
                        ]

                        totals_match = None
                        for pattern in totals_patterns:
                            totals_match = re.search(pattern, text)
                            if totals_match:
                                break

                        if totals_match:
                            totals = {
                                'Y': int(totals_match.group(1)),
                                'N': int(totals_match.group(2)),
                                'E': 0,
                                'A': 0,
                            }
                        else:
                            print(f"Warning: Could not extract vote totals in {pdf_file}")
                            continue

                        # Parse votes
                        vote_pattern = re.compile(r'([YN])((?:Mc|Mac)[A-Z][a-z]+|[A-Z][a-z]+\'[A-Za-z]+|[A-Z][a-z]+(?:[- ][A-Z][a-z]+)*)', re.MULTILINE)

                        votes = []
                        for match in vote_pattern.finditer(text):
                            # Skip if the match starts with 'EAS' or contains non-name characters
                            name = match.group(2).replace('; by proxy', '').strip()
                            if name == 'EAS' or not all(c.isalpha() or c.isspace() or c in "'-" for c in name):
                                continue
                            
                            votes.append({
                                'vote': match.group(1),
                                'name': name
                            })

                        # Determine vote type
                        total_votes = totals['Y'] + totals['N']
                        if total_votes > 40:
                            vote_type = 'floor'
                        else:
                            vote_type = 'committee'

                        # Prepare final data for this PDF
                        data = {
                            "file": os.path.basename(pdf_path),
                            "url": "undefined",
                            "bill": f"{bill_type} {bill_number}",
                            "session": session_id,
                            "action_id": f"{bill_type}{bill_number}",
                            "type": vote_type,
                            "seq_number": "N/A",
                            "date": date,
                            "description": description,
                            "totals": totals,
                            "votes": votes,
                        }

                        all_data.append(data)

                        continue
# floor vote bills –– format of `007.0058.pdf`
                    else:
                         # Extract date
                        date_match = re.search(
                            r'(\bJanuary|\bFebruary|\bMarch|\bApril|\bMay|\bJune|\bJuly|\bAugust|\bSeptember|\bOctober|\bNovember|\bDecember)\s+\d{1,2},\s+\d{4}',
                            text
                        )
                        if date_match:
                            date = date_match.group(0).strip()
                            # print(f"Date found: {date}")
                        else:
                            date = None
                            print("Date not found")

                        title_line = text.split('\n', 1)[0].strip()
                        if "house" in title_line.lower():
                            seq_prefix = "H"
                        elif "senate" in title_line.lower():
                            seq_prefix = "S"
                        else:
                            seq_prefix = ""

                        # Attempt to extract sequence number
                        seq_number_match = re.search(r'SEQ(?:\.|UENCE)? NO(?:\.|):?\s*(\d+)', text)
                        if seq_number_match:
                            seq_number = seq_number_match.group(1).strip()
                            # print(f"Sequence number found: {seq_number}")
                        else:
                            seq_number = None
                            # print("Sequence number not found")

                        # Check if at least one critical piece of data was extracted
                        if not date or not seq_number:
                            # print(f"Warning: Missing date or sequence number in {pdf_file}")
                            date = date if date else "Date not found"
                            seq_number = seq_number if seq_number else "N/A"


                        # Extract description, handling multi-line cases before the vote headers
                        # Extract description
                        description_match = None

                        # Case 1: If "SPONSOR:" is present, capture the sponsor name after it.
                        description_match = re.search(
                            r'SPONSOR:\s*([^\n]+)', text
                        )

                        # If no match, default to "Description not found"
                        description = description_match.group(0).strip() if description_match else "Description not found"
                        # print(f"Description: {description}")

                        # Adjusted pattern to handle vote totals on the same line as headers
                        totals_patterns = [
                            r'AYES\s+NOES\s+EXCUSED\s+ABSENT\s*\n?\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                            r'YEAS\s+NOES\s+EXCUSED\s+ABSENT\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                        ]

                        # Loop through the patterns to find a match
                        totals_match = None
                        for pattern in totals_patterns:
                            totals_match = re.search(pattern, text)
                            if totals_match:
                                break
                            
                        if not totals_match:
                            print(f"Warning: Could not extract vote totals in {pdf_file}")
                            continue

                        totals = {
                            'Y': int(totals_match.group(1)),
                            'N': int(totals_match.group(2)),
                            'E': int(totals_match.group(3)),
                            'A': int(totals_match.group(4)),
                            }

                        total_votes = totals['Y'] + totals['N']

                        if 'Veto Override' in description:
                            vote_type = 'veto override'
                        elif total_votes > 40:
                            vote_type = 'floor'
                        else:
                            vote_type = 'committee'

                    # Extract vote section and parse votes
                    def parse_votes(result_section):
                        votes = []
                        
                        # Clean up the input text
                        result_section = re.sub(r'\bIN THE CHAIR:.*$', '', result_section, flags=re.MULTILINE)
                        
                        # Handle Mr. President specially
                        if "Mr. President" in result_section and not any(v["name"] == "PRESIDENT_PLACEHOLDER" for v in votes):
                            votes.append({"vote": "Y", "name": "PRESIDENT_PLACEHOLDER"})
                            result_section = re.sub(r'\bMr\. President\b|\bPresident\b', '', result_section)
                        
                        # Updated pattern with correct character ranges
                        pattern = r'([YN])(?:((?:Mc|Mac)[A-Z][a-z]+)|([A-Z][a-z]+\'[A-Za-z]+)|([A-Z][a-z]+(?:[- ][A-Z][a-z]+)*))'

                        matches = re.finditer(pattern, result_section)
                        
                        seen_names = set()
                        for match in matches:
                            vote = match.group(1)
                            # Take the first non-None group after the vote as the name
                            name = next((group for group in match.groups()[1:] if group is not None), None)
                            
                            if not name or name in {"I", "IR"} or name == "Mr":
                                continue
                                
                            # Clean up the name
                            name = name.strip()
                            
                            # Only add if not already seen
                            if name not in seen_names:
                                seen_names.add(name)
                                votes.append({"vote": vote, "name": name})
                        
                        return votes

                    # Example Usage
                    result_section_match = re.search(
                        r'(PASSED|FAILED)\n(.*?)(?:\n\n|$)', text, re.DOTALL
                    )
                    if not result_section_match:
                        print(f"Warning: Could not find PASSED or FAILED section in {pdf_file}")
                    else:
                        # Get the result section text
                        result_section = result_section_match.group(2)

                        # whole sheet parse rather than line by line
                        votes = parse_votes(result_section)

                        if not votes:
                            print(f"Warning: No valid votes found in {pdf_file}")
                        else:
                            print(f"Parsed votes: {votes}")


                    # was already parsing above, this is line by line. May be more accurate so leaving in if we have issues. 
                    # First, collect all votes
                    # votes = []
                    # for line in result_section.split('\n'):
                    #     line_votes = parse_votes(line)
                    #     votes.extend(line_votes)

                    # Then, create a single data entry after collecting all votes
                    data = {
                        "file": os.path.basename(pdf_path),
                        "url": "undefined",
                        "bill": f"{bill_type} {bill_number}",
                        "session": session_id,
                        "action_id": f"{bill_type}{bill_number}-{seq_number}",
                        "type": vote_type,
                        "seq_number": f"{seq_prefix}{seq_number}",
                        "date": date,
                        "description": description,
                        "totals": totals,
                        "votes": votes,
                    }

                    all_data.append(data)

            except Exception as e:
                print(f"Error processing PDF {pdf_file}: {str(e)}")

        # Get the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Prepare directory for cleaned votes (relative to the script directory)
        cleaned_dir = os.path.join(script_dir, "cleaned", f"votes-{session_id}")
        os.makedirs(cleaned_dir, exist_ok=True)

        # Save the JSON file in the cleaned directory
        output_file = os.path.join(cleaned_dir, f"{bill_type}-{bill_number}-votes.json")
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=4)

        # print(f"Votes for {bill_type}-{bill_number} saved to {output_file}")

        return all_data

def load_bill_list(session_id):
    """
    Load the list of bills from a JSON file.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, f"../list-bills-{session_id}.json")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading bill list: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get-pdf-votesheets.py <SESSION_ID>")
        sys.exit(1)

    # Get session_id from command-line arguments
    session_id = sys.argv[1]

    parser = PDFVoteParser()

    # Load bills from the JSON file
    bills = load_bill_list(session_id)
    for bill in bills:
        bill_type = bill.get("billType")
        bill_number = bill.get("billNumber")
        if bill_type and bill_number:
            result = parser.parse_pdf_vote(bill_type, bill_number, session_id)
            print(json.dumps(result, indent=4))