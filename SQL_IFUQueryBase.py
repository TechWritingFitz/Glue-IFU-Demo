import pandas as pd
import os
import sqlite3

script_dir = os.path.dirname(os.path.abspath(__file__))

excel_file_name = 'IFU_Workbook_V2_Nov24.xlsx'
excel_file_path = os.path.join(script_dir, 'IFU_Workbook_V2_Nov24.xlsx')

print(f"Attempting to load Excel file from: {excel_file_path}")

db_file_name = 'GlueApp.db'
db_file_path = os.path.join(script_dir, db_file_name)


conn = None

conn = sqlite3.connect(db_file_path)
print(f"Successfully connected to SQLite database: {db_file_path}")

try:
    
# Load each sheet
    print("Loading data from Excel sheets")
    metadata_df = pd.read_excel(excel_file_path, sheet_name='IFU_Metadata')
    sample_type_df = pd.read_excel(excel_file_path, sheet_name='SampleCollectionType')
    consumables_df = pd.read_excel(excel_file_path, sheet_name='Consumables')
    regulatory_content_df = pd.read_excel(excel_file_path, sheet_name='RegulatoryContent')
    instructional_content_df = pd.read_excel(excel_file_path, sheet_name='InstructionalContent')
    strings_df = pd.read_excel(excel_file_path, sheet_name='Strings')
    digitalifu_df = pd.read_excel(excel_file_path, sheet_name='Digital IFUs')
    videos_df = pd.read_excel(excel_file_path, sheet_name='Videos')
    temperatures_df = pd.read_excel(excel_file_path, sheet_name='Temperatures')
    designfiles_df = pd.read_excel(excel_file_path, sheet_name='DesignFiles')
    notes_df = pd.read_excel (excel_file_path, sheet_name='Notes')

    print(f"Sheets loaded successfully from Excel.")

# Insert data into the database
    print("Inserting data into SQLite database tables...")
    metadata_df.to_sql('IFU_Metadata', conn, if_exists='replace', index=False)
    sample_type_df.to_sql('SampleCollectionType', conn, if_exists='replace', index=False)
    consumables_df.to_sql('Consumables', conn, if_exists='replace', index=False)
    regulatory_content_df.to_sql('RegulatoryContent', conn, if_exists='replace', index=False)
    instructional_content_df.to_sql('InstructionalContent', conn, if_exists='replace', index=False)
    temperatures_df.to_sql('Temperatures', conn, if_exists='replace', index=False)
    strings_df.to_sql('Strings', conn, if_exists='replace', index=False)
    designfiles_df.to_sql("DesignFiles", conn, if_exists='replace', index=False)
    notes_df.to_sql("Notes", conn, if_exists='replace', index=False)
    digitalifu_df.to_sql("Digital IFUs", conn, if_exists='replace', index=False)
    videos_df.to_sql("Videos", conn, if_exists='replace', index=False)
    print(f"Data inserted into the database successfully.")

except FileNotFoundError:
    print(f"ERROR: Excel file not found at path: {excel_file_path}")
except sqlite3.Error as e_sqlite:
    print(f"SQLite error occurred: {e_sqlite}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if conn:
        conn.close()
        print("Database connection closed.")