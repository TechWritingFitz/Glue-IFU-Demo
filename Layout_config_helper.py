import fitz  # PyMuPDF
import os
import json

# --- Configuration ---
# Point this to a sample PDF of the layout you want to map
PDF_TO_MAP = "LGC_STOOL_QR_IFU_058_R0_PREACTIVATED_US_4_PG_WITH_SPANISH_V11_HR.pdf" # Make sure this is the correct filename
DEBUG_OUTPUT_PDF = "debug_grid.pdf"
# NEW: A dedicated folder to save our layout blueprint files
LAYOUT_JSON_OUTPUT_FOLDER = "layout_configs" 

# This is the main part you will edit for each new template type.
# For each page (starting with index 0), define its grid of panels.
PAGE_GRID_CONFIG = {
    # Page index: {'rows': number_of_rows, 'cols': number_of_columns}
    0: {'rows': 1, 'cols': 2},
    1: {'rows': 2, 'cols': 4},
    2: {'rows': 2, 'cols': 4},
}

def generate_and_visualize_layout(pdf_path, output_path, page_grid_config):
    """
    Generates a panel layout based on the page-by-page grid configuration,
    draws it for visual confirmation, and returns the layout dictionary.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: Input PDF not found at '{pdf_path}'")
        return None

    panel_layout = {}
    panel_counter = 1

    try:
        with fitz.open(pdf_path) as doc:
            # Loop through our page-specific grid configuration
            for page_num, grid_config in page_grid_config.items():
                if page_num >= doc.page_count:
                    print(f"Warning: Configuration found for Page {page_num + 1}, but PDF only has {doc.page_count} pages. Skipping.")
                    continue

                page = doc[page_num]
                page_width = page.rect.width
                page_height = page.rect.height
                
                num_rows = grid_config['rows']
                num_cols = grid_config['cols']
                
                panel_width = page_width / num_cols
                panel_height = page_height / num_rows

                # Generate the grid for this specific page
                for row_index in range(num_rows):
                    for col_index in range(num_cols):
                        x0 = col_index * panel_width
                        y0 = row_index * panel_height
                        x1 = (col_index + 1) * panel_width
                        y1 = (row_index + 1) * panel_height
                        
                        panel_layout[panel_counter] = {'page': page_num, 'coords': [x0, y0, x1, y1], 'orientation': 'portrait'}
                        panel_counter += 1

            # --- Draw the generated grid for visual confirmation ---
            source_doc = fitz.open(pdf_path)
            for page in source_doc:
                # --- COLOR CHANGE HERE ---
                # Now only uses red for drawing debug boxes.
                color = (1, 0, 0) # Red
                for panel_num, panel_info in panel_layout.items():
                    if panel_info['page'] == page.number:
                        rect = fitz.Rect(panel_info['coords'])
                        page.draw_rect(rect, color=color, width=1.0, fill_opacity=0.1)
                        page.insert_text(rect.top_left + (5, 15), f"P{panel_num}", color=color)

            source_doc.save(output_path, garbage=4, deflate=True, clean=True)
            return panel_layout

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# --- Main Execution (Updated to save layout to JSON file) ---
if __name__ == '__main__':
    print("--- Layout Configuration Helper ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_file_path = os.path.join(script_dir, PDF_TO_MAP)
    debug_output_file_path = os.path.join(script_dir, DEBUG_OUTPUT_PDF)
    
    # Generate the layout and the visual debug file
    generated_layout = generate_and_visualize_layout(pdf_file_path, debug_output_file_path, PAGE_GRID_CONFIG)
    
    if generated_layout:
        print(f"\nSUCCESS: A visual guide has been created at '{DEBUG_OUTPUT_PDF}'")
        
        # --- NEW: Automatically save the layout to a JSON file ---
        # Create the output folder if it doesn't exist
        layout_folder_path = os.path.join(script_dir, LAYOUT_JSON_OUTPUT_FOLDER)
        os.makedirs(layout_folder_path, exist_ok=True)
        
        # Create a descriptive filename for the JSON blueprint
        base_pdf_name = os.path.splitext(PDF_TO_MAP)[0]
        json_filename = f"layout_{base_pdf_name}.json"
        json_output_path = os.path.join(layout_folder_path, json_filename)

        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(generated_layout, f, indent=4)

        print(f"--- Layout blueprint has been saved to '{json_output_path}' ---")
        print("\nYou can now use this file as the configuration for the main extraction script.")