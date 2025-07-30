import sqlite3

# --- Configuration ---
# The name of your database file
DATABASE_FILE = "ifu_database.db"
# A list of all the tables you want to inspect
TABLES_TO_INSPECT = ["ifu_documents", "content_panels"]

def get_all_table_field_names():
    """
    Connects to the database and prints a list of all column names
    for every table specified in the TABLES_TO_INSPECT list.
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        for table_name in TABLES_TO_INSPECT:
            # The PRAGMA table_info command is a standard SQLite way to get schema information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print(f"\n--- Field Names for table '{table_name}' ---")
            if not columns:
                print("No columns found or table does not exist.")
            else:
                for col in columns:
                    # The column name is the second item (index 1) in the returned tuple
                    print(f"- {col[1]}")
            
            print("-----------------------------------------")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    get_all_table_field_names()
