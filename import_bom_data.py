import pandas as pd
import sqlite3
import os
import json

# --- 1. Configuration ---
# You MUST adjust these settings to match your BOM file's exact structure.

# --- File Configuration ---
BOM_FILENAME = "Bill of Materials-Rev_130.xlsx"
DATABASE_FILENAME = "ifu_database.db"

# --- Spreadsheet Structure Configuration ---
# These are the row numbers (zero-indexed) where your headers are located.
# From your screenshots, both seem to be on the second row (index 1).
KIT_HEADERS_ROW = 1
MATERIAL_HEADERS_ROW = 0

# This is the column number (zero-indexed) where the kit names start.
# From your screenshots, this appears to be the 6th column (index 5).
FIRST_KIT_COLUMN = 7

# --- Column & Row Identifier Configuration ---
# This is the exact text the script looks for.
# Make sure these match your spreadsheet EXACTLY.
INTERNAL_SPEC_COL = "Internal Spec Number"
MATERIAL_NAME_COL = "Material Name"
KIT_CODE_IDENTIFIER = "SAMPLE COLLECTION KIT CODE"
DISPATCH_CODE_IDENTIFIER = "DISPATCH CODE"


def import_smart_bom_data():
    """
    Reads the complex BOM spreadsheet, correctly handles multiple header rows,
    cross-references materials with kits, and updates the database.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(script_dir, BOM_FILENAME)
    if not os.path.exists(bom_path):
        print(f"ERROR: BOM file not found at '{bom_path}'")
        return

    print("Reading BOM data...")
    # Read the data twice to handle the different header rows correctly
    try:
        # Read the sheet once, without assuming a header, to find the special rows
        df_raw = pd.read_excel(bom_path, header=None)
        
        # Read it again, this time with the correct material headers
        df_materials = pd.read_excel(bom_path, header=MATERIAL_HEADERS_ROW)

    except Exception as e:
        print(f"ERROR: Could not read Excel file. Please ensure it is not password protected. Details: {e}")
        return

    # --- Stage 1: Process the horizontal Kit and Dispatch Codes ---
    print("Processing Kit and Dispatch codes...")
    kit_lookup = {}
    kit_columns = df_materials.columns[FIRST_KIT_COLUMN:]
    
    # --- FIX: Use the raw dataframe (df_raw) to find the special rows ---
    # Convert the first column to string type and strip whitespace to ensure a clean match
    search_column = df_raw[0].astype(str).str.strip()
    
    dispatch_row_df = df_raw[search_column == DISPATCH_CODE_IDENTIFIER]
    kit_code_row_df = df_raw[search_column == KIT_CODE_IDENTIFIER]
    
    if dispatch_row_df.empty or kit_code_row_df.empty:
        # Corrected the error message to be more helpful
        print("FATAL ERROR: Could not find the 'DISPATCH CODE' or 'SAMPLE COLLECTION KIT CODE' identifier rows.")
        print(f"Please check that the text '{DISPATCH_CODE_IDENTIFIER}' and '{KIT_CODE_IDENTIFIER}' exist in the first column of your spreadsheet.")
        return

    dispatch_row = dispatch_row_df.iloc[0]
    kit_code_row = kit_code_row_df.iloc[0]

    for i, kit_name in enumerate(df_materials.columns):
        if i < FIRST_KIT_COLUMN:
            continue
        # Skip any non-string or empty kit names
        if not isinstance(kit_name, str) or "Unnamed" in kit_name:
            continue
        dispatch_code = dispatch_row.get(i)
        kit_code = kit_code_row.get(i)
        kit_lookup[kit_name] = {"dispatch_code": dispatch_code, "kit_code": kit_code}
    
    print(f"  -> Found {len(kit_lookup)} kits.")

    # --- Stage 2: Process the vertical material list ---
    print("Processing material list and cross-referencing with kits...")
    df_materials_clean = df_materials.dropna(subset=[INTERNAL_SPEC_COL]).copy()
    
    db_updates = {}

    for index, row in df_materials_clean.iterrows():
        spec_num = str(row[INTERNAL_SPEC_COL]).strip()
        material_name = str(row[MATERIAL_NAME_COL])
        
        kits_for_this_material = []
        for kit_name in kit_lookup.keys():
            if kit_name in row and row[kit_name] == 1:
                kits_for_this_material.append(kit_name)
        
        sample_type = "Unknown"
        if "IFU" in spec_num:
            if "Blood" in material_name: sample_type = "Blood"
            elif "Urine" in material_name: sample_type = "Urine"
            elif "Saliva" in material_name: sample_type = "Saliva"
            elif "Vaginal" in material_name: sample_type = "Vaginal"

        for kit_name in kits_for_this_material:
            kit_info = kit_lookup.get(kit_name, {})
            consumable_list = df_materials_clean[df_materials_clean[kit_name] == 1][MATERIAL_NAME_COL].tolist()
            update_key = (spec_num, kit_info.get('kit_code'))
            db_updates[update_key] = {
                "part_number": spec_num, "sample_type": sample_type, "market": "US", # Placeholder for market
                "dispatch_code": kit_info.get('dispatch_code'), "kit_code": kit_info.get('kit_code'),
                "consumables": json.dumps(consumable_list)
            }

    # --- Stage 3: Update the database ---
    print("\nUpdating the database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    cursor = conn.cursor()
    update_count = 0

    for key, data in db_updates.items():
        if "IFU" not in data["part_number"]:
            continue
            
        print(f"  -> Updating data for Part Number: {data['part_number']}")
        cursor.execute('''
            UPDATE ifu_documents
            SET sample_type = ?, market = ?, dispatch_code = ?, kit_code = ?, consumables = ?
            WHERE part_number = ?
        ''', (
            data['sample_type'], data['market'], data['dispatch_code'], 
            data['kit_code'], data['consumables'], data['part_number']
        ))
        if cursor.rowcount > 0:
            update_count += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"\n--- Smart BOM Import Complete. Updated {update_count} database entries. ---")

if __name__ == '__main__':
    import_smart_bom_data()
