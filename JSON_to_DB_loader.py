import sqlite3
import os
import json
import re
import hashlib
from datetime import datetime

# --- 1. Configuration ---
LAYOUT_CONFIG_FOLDER = "layout_configs" 
BATCH_OUTPUT_FILE = "batch_extraction_output.json" 
DATABASE_FILE = "ifu_database.db"

# This dictionary should be kept in sync with the mapping in your PDF extraction script.
LAYOUT_MAPPING = {
    "IFU-111": "26panel_layout.json",
    "IFU-098": "22panel_layout.json",
    "IFU-241": "18panel_layout.json",
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
    "IFU-242": "18panel_layout.json"
}

# --- 2. Database Setup ---

def initialize_database():
    """
    Sets up the SQLite database and creates the new two-table schema.
    This granular structure allows us to track individual panels and their content hash.
    """
    print(f"Initializing database at '{DATABASE_FILE}'...")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Table 1: Stores metadata for each unique IFU document version.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ifu_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            document_version TEXT NOT NULL,
            language TEXT NOT NULL,
            source_filename TEXT,
            created_at TIMESTAMP,
            UNIQUE(part_number, document_version, language)
        )
    ''')

    # Table 2: Stores the content of each individual panel.
    # Each row links back to a document in the ifu_documents table.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            panel_number INTEGER NOT NULL,
            panel_type TEXT,
            content_text TEXT,
            content_hash TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES ifu_documents (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully with two-table schema.")

# --- 3. Data Parsing & Hashing Helpers ---

def get_metadata_from_text(text):
    """Uses regular expressions to find the Part Number and Version from text."""
    # UPDATED REGEX: Now accepts letters and numbers after 'R', like 'RA' or 'R1A'
    match = re.search(r'((?:QR-)?IFU-\d+)[-\s]+(R[A-Z0-9]+)', text, re.IGNORECASE)
    if match:
        part_number, version = match.groups()
        return part_number.upper().replace("_","-"), version.upper()
    return None, None

def get_panel_type(panel_num, panel_types_dict):
    """Finds the semantic type of a panel (e.g., 'instructional', 'regulatory')."""
    for p_type, p_nums in panel_types_dict.items():
        if panel_num in p_nums:
            return p_type.replace("_panels_en", "").replace("_panels_es", "")
    return "unknown"

def generate_hash(text):
    """Generates a SHA-256 hash for a given block of text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# --- 4. Main Processing Logic ---

def process_and_load_data():
    """
    Main function to read the batch JSON, process each document, and load the 
    data into the new two-table database structure, with hashing for each panel.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    batch_file_path = os.path.join(script_dir, BATCH_OUTPUT_FILE)
    layout_folder_path = os.path.join(script_dir, LAYOUT_CONFIG_FOLDER)

    if not os.path.exists(batch_file_path):
        print(f"FATAL ERROR: Batch output file not found at '{batch_file_path}'.")
        return

    with open(batch_file_path, 'r', encoding='utf-8') as f:
        all_documents_data = json.load(f)

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    for filename, panel_data in all_documents_data.items():
        print(f"\n--- Processing: {filename} ---")
        if "error" in panel_data:
            print("  -> SKIPPING: File has an extraction error.")
            continue

        layout_key = next((key for key in LAYOUT_MAPPING if key in filename.replace("_", "-")), None)
        if not layout_key:
            print(f"  -> SKIPPING: Could not find a key in LAYOUT_MAPPING for this filename.")
            continue
        
        layout_filename = LAYOUT_MAPPING[layout_key]
        layout_filepath = os.path.join(layout_folder_path, layout_filename)

        try:
            with open(layout_filepath, 'r', encoding='utf-8') as f:
                layout_config = json.load(f)
        except FileNotFoundError:
            print(f"  -> SKIPPING: Layout file '{layout_filename}' not found.")
            continue

        panel_types = layout_config.get("panel_types", {})
        # Added debug print to show what text is being searched
        metadata_panel_nums = panel_types.get("metadata", [])
        metadata_text = "".join(panel.get("english", "") + panel.get("spanish", "") for num_str, panel in panel_data.items() if int(num_str) in metadata_panel_nums)
        print(f"  -> Searching for metadata in text: '{metadata_text[:100]}...'")

        part_number, doc_version = get_metadata_from_text(metadata_text)

        if not part_number:
            print(f"  -> SKIPPING: Could not extract Part Number and Version from metadata text.")
            continue

        print(f"  -> Identified Part Number: {part_number}, Version: {doc_version}")

        # Process each language
        for lang in ["english", "spanish"]:
            lang_content_exists = any(p.get(lang) for p in panel_data.values())
            if not lang_content_exists:
                continue

            cursor.execute('''
                INSERT OR IGNORE INTO ifu_documents (part_number, document_version, language, source_filename, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (part_number, doc_version, lang, datetime.now(), filename))
            
            cursor.execute('SELECT id FROM ifu_documents WHERE part_number=? AND document_version=? AND language=?', (part_number, doc_version, lang))
            doc_id_tuple = cursor.fetchone()
            if not doc_id_tuple:
                print(f"  -> CRITICAL ERROR: Could not retrieve doc_id for {part_number} {doc_version} ({lang}).")
                continue
            doc_id = doc_id_tuple[0]

            cursor.execute('DELETE FROM content_panels WHERE document_id = ?', (doc_id,))
            print(f"  -> Cleared old panels for {part_number} {doc_version} ({lang})...")

            for panel_num_str, content_dict in panel_data.items():
                text = content_dict.get(lang)
                if not text: continue

                panel_num = int(panel_num_str)
                panel_type = get_panel_type(panel_num, panel_types)
                text_hash = generate_hash(text)

                print(f"    -> Inserting Panel {panel_num} ({panel_type}), Hash: {text_hash[:8]}...")
                cursor.execute('''
                    INSERT INTO content_panels (document_id, panel_number, panel_type, content_text, content_hash)
                    VALUES (?, ?, ?, ?, ?)
                ''', (doc_id, panel_num, panel_type, text, text_hash))

    conn.commit()
    conn.close()
    print("\n--- Database processing complete. ---")

# --- 5. Execution Block ---
if __name__ == '__main__':
    initialize_database()
    process_and_load_data()
