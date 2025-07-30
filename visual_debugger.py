import fitz  # PyMuPDF
import os

# --- Configuration ---
PDF_FILENAME = "LGC_VERILY_ACC_BLOOD_DBS_QR_IFU_021_R0_PREACTIVATED_US_5_PG_WITH_SPANISH_V7_HR.pdf"
DEBUG_OUTPUT_PDF = "debug_layout.pdf"

# --- PASTE YOUR CURRENT PANEL_LAYOUT HERE ---
# Copy the PANEL_LAYOUT dictionary from your pdf_extractor.py file and paste it here.
# I'm using the example values, but you should use your own.
PANEL_LAYOUT = {
    # Replace these example coordinates with your own accurate ones
    # Panel Number: 1 coordinates
    1:  {'page': 0, 'coords': (66, 65, 345, 465)},
    # Panel Number: 2 
    2:  {'page': 0, 'coords': (355, 80, 595, 370)},
    # Panel Number: 3
    3: {'page': 1, 'coords': ()},
    #Panel Number: 4
    4: {'page': 1, 'coords': ()},
}

def draw_panel_boxes(pdf_path, output_path):
    """
    Opens a PDF and draws colored rectangles on it based on the
    PANEL_LAYOUT dictionary to help visualize the parsing areas.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: Input PDF not found at '{pdf_path}'")
        return

    # Use a list of colors to make each panel box distinct
    colors = [
        (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1),
        (1, 0, 1), (1, 0.5, 0), (0.5, 0, 1), (0, 0.5, 0), (0.5, 1, 0.5)
    ]

    try:
        doc = fitz.open(pdf_path)
        
        # Draw on all pages
        for page in doc:
            for i, (panel_num, coords) in enumerate(PANEL_LAYOUT.items()):
                # Create a fitz.Rect object from the coordinates
                rect = fitz.Rect(coords)
                # Choose a color for the box border
                color = colors[i % len(colors)] # Cycle through colors
                
                # Draw the rectangle on the page
                page.draw_rect(rect, color=color, width=1.5)
                
                # Add a text label to the corner of the box
                page.insert_text(rect.top_left + (5, 15), f"P{panel_num}", color=color)

        # Save the modified PDF with the drawings
        doc.save(output_path, garbage=1, deflate=True, clean=True)
        print(f"\nSUCCESS: A new file '{output_path}' has been created with the panel boxes drawn on it.")

    except Exception as e:
        print(f"An error occurred: {e}")

# --- Main Execution ---
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_file_path = os.path.join(script_dir, PDF_FILENAME)
    output_file_path = os.path.join(script_dir, DEBUG_OUTPUT_PDF)
    
    draw_panel_boxes(pdf_file_path, output_file_path)