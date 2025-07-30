import fitz  # PyMuPDF
import os

# --- Configuration ---
# Make sure this points to your sample PDF
PDF_FILENAME = "LGC_VERILY_ACC_BLOOD_DBS_QR_IFU_021_R0_PREACTIVATED_US_5_PG_WITH_SPANISH_V7_HR.pdf"
OUTPUT_MAP_FILE = "pdf_coordinates_map.txt"

def create_coordinate_map(pdf_path):
    """
    Analyzes a PDF and creates a text file mapping text blocks to their coordinates.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at '{pdf_path}'")
        return None

    output_lines = []
    try:
        with fitz.open(pdf_path) as doc:
            # Add the overall page dimensions to the top of the map file
            if doc.page_count > 0:
                first_page_rect = doc[0].rect
                output_lines.append(f"PAGE DIMENSIONS: Width={first_page_rect.width}, Height={first_page_rect.height}\n")
                output_lines.append("="*60 + "\n")

            # Loop through all pages to get all content
            for page_num, page in enumerate(doc):
                output_lines.append(f"--- PAGE {page_num + 1} ---\n")
                
                # Get text "blocks" which are better for this than individual words
                blocks = page.get_text("blocks")
                # Sort blocks by reading order to make the map file easier to follow
                blocks.sort(key=lambda b: (b[1], b[0])) # Sort by top, then left
                
                for b in blocks:
                    # b is a tuple: (x0, y0, x1, y1, text, block_no, block_type)
                    x0, y0, x1, y1, text, _, _ = b
                    # Clean the text for a single-line display
                    clean_text = text.replace('\n', ' ').strip()
                    # Format the line for the map file
                    line = f"COORDS: (x0={x0:.1f}, y0={y0:.1f}, x1={x1:.1f}, y1={y1:.1f}) | TEXT: {clean_text}\n"
                    output_lines.append(line)
                output_lines.append("\n") # Add a space between pages

    except Exception as e:
        print(f"An error occurred while creating the coordinate map: {e}")
        return None
        
    return "".join(output_lines)

# --- Main Execution ---
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_file_path = os.path.join(script_dir, PDF_FILENAME)
    
    map_content = create_coordinate_map(pdf_file_path)
    
    if map_content:
        output_file_path = os.path.join(script_dir, OUTPUT_MAP_FILE)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(map_content)
        print(f"SUCCESS: A coordinate map has been created at '{output_file_path}'")
        print("Please use THIS NEW FILE to configure the PANEL_LAYOUT in your main script.")