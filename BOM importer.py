import pandas as pd
import sqlite3
import os
import json
import re

# --- 1. Configuration ---
# This script is designed to read the new, transposed (columns-as-IFUs) spreadsheet.

BOM_FILENAME = "BOM extraction mock-up.xlsx"  # The name of your new transposed BOM file.
DATABASE_FILENAME = "ifu_database.db"

def import_transposed_bom_data():
    """
    Reads a transposed BOM spreadsheet, handles one-to-many relationships by
    aggregating data into JSON lists, and updates the database.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bom_path = os.path.join(script_dir, BOM_FILENAME)
    if not os.path.exists(bom_path):
        print(f"ERROR: Clean BOM file not found at '{bom_path}'")
        return

    print("Reading transposed BOM data...")
    try:
        # Use the first column ("Field") as the index for easy lookups
        df = pd.read_excel(bom_path, index_col=0) 
    except Exception as e:
        print(f"ERROR: Could not read Excel file. Details: {e}")
        return

    # Connect to the database
    conn = sqlite3.connect(DATABASE_FILENAME)
    cursor = conn.cursor()
    update_count = 0

    # Loop through each COLUMN in the spreadsheet (each column is an IFU)
    for part_num_with_rev in df.columns:
        try:
            # --- NEW LOGIC: Strip the revision number to match the database format ---
            # This regex finds the base part number (e.g., "QR-IFU-115") from "QR-IFU-115-R0"
            match = re.match(r'(QR-IFU-\d+)', part_num_with_rev)
            if not match:
                print(f"  -> INFO: Skipping column '{part_num_with_rev}' as it does not look like a valid Part Number.")
                continue
            part_num = match.group(1)
            
            print(f"  -> Processing Part Number: {part_num} (from column {part_num_with_rev})")
            
            # Get the series of data for the current IFU column
            ifu_data = df[part_num_with_rev]

            # Aggregate multiple rows into lists
            kit_codes = [v for k, v in ifu_data.items() if 'Kit Code' in k and pd.notna(v)]
            dispatch_codes = [v for k, v in ifu_data.items() if 'Dispatch Code' in k and pd.notna(v)]
            sample_types = [v for k, v in ifu_data.items() if 'Sample Collection Type' in k and pd.notna(v)]
            consumables = [v for k, v in ifu_data.items() if 'Consumable Name' in k and pd.notna(v)]
            
            market = next((v for k, v in ifu_data.items() if 'Market' in k and pd.notna(v)), "US")

            # Execute the UPDATE query for the matching part number
            cursor.execute('''
                UPDATE ifu_documents
                SET 
                    sample_type = ?, 
                    market = ?, 
                    dispatch_code = ?, 
                    kit_code = ?, 
                    consumables = ?
                WHERE part_number = ?
            ''', (
                json.dumps(sample_types),   # Store list as JSON string
                str(market),
                json.dumps(dispatch_codes), # Store list as JSON string
                json.dumps(kit_codes),      # Store list as JSON string
                json.dumps(consumables),    # Store list as JSON string
                part_num # Use the cleaned part number for the lookup
            ))
            
            if cursor.rowcount > 0:
                update_count += cursor.rowcount
                print(f"    -> SUCCESS: Updated {cursor.rowcount} record(s) in the database.")
            else:
                print(f"    -> INFO: No existing record found in the database for Part Number {part_num}.")

        except Exception as e:
            print(f"An unexpected error occurred while processing {part_num_with_rev}: {e}")
            continue

    conn.commit()
    conn.close()
    
    print(f"\n--- Transposed BOM Import Complete ---")
    print(f"A total of {update_count} database entries were updated.")

if __name__ == '__main__':
    import_transposed_bom_data()
