import fitz  # PyMuPDF
import os

# --- Configuration ---
PDF_FILENAME = "LGC_VERILY_ACC_BLOOD_DBS_QR_IFU_021_R0_PREACTIVATED_US_5_PG_WITH_SPANISH_V7_HR.pdf"

def run_word_level_diagnostics(pdf_path):
    """
    This function extracts every single word from ALL pages of the PDF,
    sorts them into a single reading order, and prints them.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at '{pdf_path}'")
        return

    print(f"--- Running Word-Level Diagnostics on '{pdf_path}' ---")
    
    try:
        with fitz.open(pdf_path) as doc:
            print(f"PDF has {doc.page_count} pages. Processing all of them...")
            all_words = []
            
            # 1. Loop through ALL pages
            for page_num, page in enumerate(doc):
                # 2. Extract individual words with coordinates
                # Each 'word' is a tuple: (x0, y0, x1, y1, "word_text", ...)
                page_words = page.get_text("words")
                
                # We add the page number to each word's data for later reference
                # New format: (x0, y0, x1, y1, "word_text", page_num)
                all_words.extend([w[:5] + (page_num,) for w in page_words])

            # 3. Sort ALL words from the entire document together
            # We sort by page number first, then vertical position, then horizontal
            all_words.sort(key=lambda word: (word[5], word[1], word[0]))

            # Return just the text of each word in the correct order
            return [word[4] for word in all_words]

    except Exception as e:
        print(f"An error occurred during diagnostics: {e}")

# --- Main Execution ---
if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_file_path = os.path.join(script_dir, PDF_FILENAME)
    
    sorted_words = run_word_level_diagnostics(pdf_file_path)
    
    if sorted_words:
        print(f"\nSUCCESS: Found and sorted {len(sorted_words)} words from the entire document.")
        
        # We will join the words into a single string for the text file
        # to make it easier to read and search.
        full_text_from_words = " ".join(sorted_words)
        
        output_file_path = os.path.join(script_dir, "sorted_word_output.txt")
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(full_text_from_words)
        
        print(f"\n--- A single string of all sorted words has been saved to '{output_file_path}' ---")
        print("Please open this file and check if the previously missing section titles are now present.")
    else:
        print("\nINFO: No words were extracted from the PDF.")