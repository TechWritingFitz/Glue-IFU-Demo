import fitz  # PyMuPDF
import os
from collections import defaultdict

# --- Configuration ---
# Point this to the folder with your batch of PDFs
PDF_FOLDER_NAME = "PDF repository copy"

def generate_layout_fingerprint(pdf_path):
    """
    Analyzes a PDF and generates a unique "fingerprint" based on its structure.
    """
    try:
        with fitz.open(pdf_path) as doc:
            # The fingerprint is based on page count, and the number of text blocks on each page
            page_count = doc.page_count
            block_counts = [len(page.get_text("blocks")) for page in doc]
            
            # We combine these into a simple, unique string
            fingerprint = f"pages:{page_count}|blocks:{','.join(map(str, block_counts))}"
            return fingerprint
    except Exception as e:
        return f"Error: {e}"

# --- Main Execution ---
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_folder_path = os.path.join(script_dir, PDF_FOLDER_NAME)

    if not os.path.isdir(pdf_folder_path):
        print(f"Error: Folder '{pdf_folder_path}' not found.")
    else:
        pdf_files = [f for f in os.listdir(pdf_folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in the folder '{PDF_FOLDER_NAME}'.")
        else:
            print(f"Analyzing layouts for {len(pdf_files)} PDF files...")
            
            # A dictionary to group files by their layout fingerprint
            layout_groups = defaultdict(list)

            for filename in pdf_files:
                file_path = os.path.join(pdf_folder_path, filename)
                fingerprint = generate_layout_fingerprint(file_path)
                layout_groups[fingerprint].append(filename)

            # --- Print the Final Report ---
            print("\n--- Layout Analysis Report ---")
            if len(layout_groups) == 1:
                print("Success! All PDFs appear to share the same layout.")
            else:
                print(f"Found {len(layout_groups)} unique layouts in the provided documents.")

            for i, (fingerprint, files) in enumerate(layout_groups.items()):
                print(f"\n--- Layout Template #{i+1} ---")
                print(f"  Files with this layout ({len(files)}):")
                for file in files:
                    print(f"    - {file}")