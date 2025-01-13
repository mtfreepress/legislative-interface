import os
import json

def extract_names(input_path, output_path=None):
    """
    Extracts names from a legislators JSON file in the format LastName, FirstName.
    
    Args:
        input_path (str): Path to the input JSON file.
        output_path (str, optional): Path to save the output JSON file. If None, just returns the list.
        
    Returns:
        list: A list of names in LastName, FirstName format.
    """
    try:
        # Read the JSON file
        with open(input_path, 'r') as file:
            legislators = json.load(file)
        
        # Extract names in LastName, FirstName format
        names = []
        for legislator in legislators:
            first_name = legislator.get("firstName", "").strip()
            last_name = legislator.get("lastName", "").strip()
            if first_name and last_name:
                names.append(f"{last_name}, {first_name}")
        
        # Save to output file if specified
        if output_path:
            with open(output_path, 'w') as file:
                json.dump(names, file, indent=2)
        
        return names

    except Exception as e:
        print(f"Error: {e}")
        return []

# Usage Example
if __name__ == "__main__":
    # Set up file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    legislators_file = os.path.join(script_dir, "../inputs/legislators/legislators.json")
    output_file = os.path.join(script_dir, "legislator_names.json")

    # Extract names
    names_list = extract_names(legislators_file, output_file)

    # Print result
    print(f"Extracted {len(names_list)} names:")
    print("\n".join(names_list))
