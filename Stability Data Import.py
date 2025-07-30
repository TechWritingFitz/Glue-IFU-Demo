import pandas as pd
import sqlite3
import os

# --- 1. Configuration ---
# You MUST adjust these settings to match your stability table file.

STABILITY_FILE = "Stability Data Import.xlsx"  # The name of your stability data file.
DATABASE_FILE = "ifu_database.db"

# The exact names of the columns in your spreadsheet.
TEST_NAME = "Test name"
KIT_CODE_COL = "Kit Code"
BIOMARKERS_COL = "Biomarkers"
COUNTRY_COL = "Country"
NY_COL = "NY?"
AVAILABILITY_COL = "Availability Status"
SAMPLE_COLLECTION_TYPE_COL = "Sample Type"
MESSAGING_TYPE_COL = "Messaging Type"

def add_stability_column_to_db():
    """Ensures the 'stability_type' column exists in the database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE ifu_documents ADD COLUMN stability_type TEXT')
        print("  -> Added 'stability_type' column to 'ifu_documents' table.")
    except sqlite3.OperationalError:
        # Column already exists, which is fine.
        pass
    conn.commit()
    conn.close()


def import_stability_data():
    """
    Reads the stability table spreadsheet and updates the database
    with the stability type ('General' or 'Specific') for each matching kit code.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    stability_path = os.path.join(script_dir, STABILITY_FILE)
    
    if not os.path.exists(stability_path):
        print(f"FATAL ERROR: Stability file not found at '{stability_path}'.")
        return

    print(f"Reading data from '{STABILITY_FILE}'...")
    try:
        df = pd.read_excel(stability_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Connect to the database
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    update_count = 0

    # Loop through each row in the spreadsheet
    for index, row in df.iterrows():
        try:
            kit_code = str(row[KIT_CODE_COL]).strip()
            approval_status = str(row[MESSAGING_TYPE_COL]).strip().lower()

            # Determine stability type based on the approval column
            stability_type = "General" if approval_status == "yes" else "Specific"
            
            print(f"  -> Processing Kit Code: {kit_code}, Stability Type: {stability_type}")

            # Find all IFUs that use this kit code and update them.
            # We must search within the JSON string in the 'kit_code' column.
            cursor.execute('''
                UPDATE ifu_documents
                SET stability_type = ?
                WHERE kit_code LIKE ?
            ''', (stability_type, f'%"{kit_code}"%'))
            
            if cursor.rowcount > 0:
                update_count += cursor.rowcount
                print(f"    -> SUCCESS: Updated {cursor.rowcount} record(s) in the database.")

        except KeyError as e:
            print(f"\nFATAL ERROR: A column name is incorrect.")
            print(f"The column '{e}' was not found in your spreadsheet.")
            conn.close()
            return
        except Exception as e:
            print(f"An unexpected error occurred on row {index}: {e}")
            continue

    conn.commit()
    conn.close()
    
    print(f"\n--- Stability Data Import Complete ---")
    print(f"A total of {update_count} database entries were updated.")

if __name__ == '__main__':
    add_stability_column_to_db() # First, make sure the column exists
    import_stability_data()

