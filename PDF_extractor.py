import fitz  # PyMuPDF
import os
import json

# --- 1. Main Configuration ---
PDF_FOLDER_NAME = "REPOSITORY FOR PROCESSING" # The folder with the PDFs you want to process
LAYOUT_CONFIG_FOLDER = "layout_configs" # The folder where you save your JSON blueprints

# This dictionary is the "switchboard". It tells the script which layout blueprint
# to use for a document. The key should be a unique part of a PDF's filename.
LAYOUT_MAPPING = {
    "IFU-111": "26panel_layout.json",
    "IFU-098": "22panel_layout.json",
    "IFU-241": "22panel_layout.json",
    "IFU-122": "14bpanel_layout.json",
    "IFU-064": "12panel_layout.json",
    "IFU-063": "10panel_layout.json",
    "IFU-115": "8panel_layout.json",
    "IFU-203": "12panel_layout.json",
    "IFU-204": "22panel_layout.json",
    "IFU-123": "10panel_layout.json",
    "IFU-097": "14apanel_layout.json",
    "IFU-021": "22panel_layout.json",
    "IFU-120": "10panel_layout.json",
    "IFU-062": "12panel_layout.json",
    "IFU-061": "12panel_layout.json",
    "IFU-094": "26panel_layout.json",
    "IFU-240": "18panel_layout.json",
    "IFU-242": "18panel_layout.json",
    "IFU-016": "",
    "IFU-117": ""
}


# --- 2. Helper Functions ---
def clean_parsed_text(text):
    """
    Cleans up common text extraction issues like ligatures and extra whitespace.
    """
    # --- FIX: Expanded ligature map to catch more common cases ---
    ligatures = {
        '\ufb00': 'ff',
        '\ufb01': 'fi',
        '\ufb02': 'fl',
        '\ufb03': 'ffi',
        '\ufb04': 'ffl',
        '\ufb05': 'ft',
        '\ufb06': 'st',
    }
    for search, replace in ligatures.items():
        text = text.replace(search, replace)
        
    return ' '.join(text.split())


# --- 3. Core Parsing Function ---
def parse_document_by_words_and_layout(pdf_path, layout_config):
    """
    Extracts words and assigns them to panels based on the provided layout configuration.
    """
    panel_layout = layout_config.get("panel_layout", {})
    panel_types = layout_config.get("panel_types", {})
    
    # Get all panel type definitions for easy lookup
    english_panels = set(
        panel_types.get("metadata", []) +
        panel_types.get("title_page_en", []) +
        panel_types.get("instructional_panels_en", []) +
        panel_types.get("regulatory_panels_en", [])
    )
    regulatory_panels_en = panel_types.get("regulatory_panels_en", [])
    
    try:
        with fitz.open(pdf_path) as doc:
            all_words = []
            for page_num, page in enumerate(doc):
                page_words = page.get_text("words")
                all_words.extend([w + (page_num,) for w in page_words])

            final_content = {}
            for panel_num_str, panel_info in panel_layout.items():
                panel_num = int(panel_num_str)
                print(f"\n  --- Processing Panel {panel_num} ---")
                
                panel_page = panel_info['page']
                
                # --- Explicit Column Processing Logic for Regulatory Panels ---
                if 'columns' in panel_info:
                    print(f"  -> Applying EXPLICIT column logic for regulatory panel.")
                    column_texts = []
                    for i, col_info in enumerate(panel_info['columns']):
                        cx0, cy0, cx1, cy1 = col_info['coords']
                        col_words = [w for w in all_words if w[8] == panel_page and cx0 <= w[0] < cx1 and cy0 <= w[1] < cy1]
                        col_words.sort(key=lambda w: (w[1], w[0]))
                        column_text = clean_parsed_text(" ".join([w[4] for w in col_words]))
                        column_texts.append(column_text)
                    
                    final_text = "\n\n".join(column_texts)
                    
                    if panel_num in regulatory_panels_en:
                         final_content[panel_num] = {"english": final_text, "spanish": ""}
                    else:
                         final_content[panel_num] = {"english": "", "spanish": final_text}

                else: # --- Standard Logic for all other panel types ---
                    print(f"  -> Applying standard logic.")
                    px0, py0, px1, py1 = panel_info['coords']
                    words_in_panel = [w for w in all_words if w[8] == panel_page and px0 <= w[0] < px1 and py0 <= w[1] < py1]

                    # --- FIX: If a panel is defined as English, treat ALL its text as English ---
                    if panel_num in english_panels:
                        print("  -> FIX: English-only panel type detected. Bypassing language split.")
                        words_in_panel.sort(key=lambda w: (w[1], w[0]))
                        english_text = clean_parsed_text(" ".join([w[4] for w in words_in_panel]))
                        final_content[panel_num] = {"english": english_text, "spanish": ""}
                    else: # It's a Spanish or mixed panel, so we do the split
                        orientation = panel_info.get('orientation', 'portrait')
                        english_col_words, spanish_col_words = [], []
                        language_separator_x = doc[0].rect.width / 2

                        for word in words_in_panel:
                            if word[0] < language_separator_x:
                                english_col_words.append(word)
                            else:
                                spanish_col_words.append(word)

                        if orientation == 'landscape':
                            english_col_words.sort(key=lambda w: (w[0], w[1]))
                            spanish_col_words.sort(key=lambda w: (w[0], w[1]))
                        else:
                            english_col_words.sort(key=lambda w: (w[1], w[0]))
                            spanish_col_words.sort(key=lambda w: (w[1], w[0]))
                        
                        # In this case, we assume the primary language is Spanish and any English is incidental
                        english_text = clean_parsed_text(" ".join([w[4] for w in english_col_words]))
                        spanish_text = clean_parsed_text(" ".join([w[4] for w in spanish_col_words]))
                        combined_text = f"{english_text} {spanish_text}".strip()
                        final_content[panel_num] = {"english": "", "spanish": clean_parsed_text(combined_text)}
        return final_content

    except Exception as e:
        return {"error": f"An error occurred during parsing: {e}"}


# --- 4. Main Execution Block ---
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_folder_path = os.path.join(script_dir, PDF_FOLDER_NAME)
    layout_folder_path = os.path.join(script_dir, LAYOUT_CONFIG_FOLDER)

    if not os.path.isdir(pdf_folder_path):
        print(f"Error: PDF folder '{pdf_folder_path}' not found.")
    else:
        pdf_files_to_process = [f for f in os.listdir(pdf_folder_path) if f.lower().endswith('.pdf')]
        all_documents_data = {}

        for filename in pdf_files_to_process:
            print(f"\nProcessing file: {filename}")
            
            normalized_filename = filename.replace("_", "-").upper()
            layout_key = next((key for key in LAYOUT_MAPPING if key.upper() in normalized_filename), None)
            
            if not layout_key:
                print(f"  -> WARNING: No layout mapping found for '{filename}'. Skipping file.")
                all_documents_data[filename] = {"error": "No matching layout configuration found."}
                continue

            print(f"  -> Found matching layout key: '{layout_key}'")
            layout_filename = LAYOUT_MAPPING[layout_key]
            layout_filepath = os.path.join(layout_folder_path, layout_filename)
            
            try:
                with open(layout_filepath, 'r', encoding='utf-8') as f:
                    active_layout_config = json.load(f)
            except FileNotFoundError:
                print(f"  -> ERROR: Layout file '{layout_filename}' not found. Skipping file.")
                all_documents_data[filename] = {"error": f"Layout file not found: {layout_filename}"}
                continue

            file_path = os.path.join(pdf_folder_path, filename)
            parsed_data = parse_document_by_words_and_layout(file_path, active_layout_config)
            
            all_documents_data[filename] = parsed_data

        output_file_path = os.path.join(script_dir, "batch_extraction_output.json")
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(all_documents_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n--- Batch processing complete. All results saved to '{output_file_path}' ---")
