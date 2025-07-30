import sqlite3
import json
import os
import difflib
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict
from datetime import datetime

def parse_jira_description(description_obj):
    """
    Parses Jira's structured document format to extract plain text.
    """
    full_text = []
    if not description_obj or 'content' not in description_obj:
        return ""
        
    for paragraph_block in description_obj['content']:
        if 'content' in paragraph_block:
            for text_block in paragraph_block['content']:
                if 'text' in text_block:
                    full_text.append(text_block['text'])
    return "\n".join(full_text)

# --- 1. Configuration ---
DATABASE_FILE = 'ifu_database.db'
CHECKLIST_DATA_FILE = os.path.join('generated_checklists', 'generated_checklist_data.json')

# --- 2. Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- 3. Helper Function ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- 4. API Endpoints ---

@app.route('/api/ifus', methods=['GET'])
def get_all_ifus():
    """Endpoint to fetch a list of all unique IFU documents, including ID."""
    conn = get_db_connection()
    ifus = conn.execute('SELECT DISTINCT id, part_number, document_version, language FROM ifu_documents ORDER BY part_number, document_version').fetchall()
    conn.close()
    return jsonify([dict(row) for row in ifus])

@app.route('/api/ifu/<int:document_id>', methods=['GET'])
def get_ifu_details(document_id):
    """Endpoint to fetch all content panels for a single IFU document."""
    conn = get_db_connection()
    panels = conn.execute('SELECT * FROM content_panels WHERE document_id = ? ORDER BY panel_number', (document_id,)).fetchall()
    conn.close()
    if not panels:
        return jsonify({"error": "Document not found"}), 404
    return jsonify([dict(row) for row in panels])
    
@app.route('/api/ifu-by-part-number/<string:part_number>/<string:doc_version>', methods=['GET'])
def get_ifu_by_part_number(part_number, doc_version):
    """Fetches all enriched metadata for a specific IFU part_number and version."""
    conn = get_db_connection()
    records = conn.execute("SELECT * FROM ifu_documents WHERE part_number = ? AND document_version = ?", (part_number, doc_version)).fetchall()
    conn.close()
    if not records:
        return jsonify({"error": "IFU not found"}), 404
    
    kit_codes, consumables, sample_types = set(), set(), set()
    for record in records:
        if record['kit_code'] and record['kit_code'] != '[]': kit_codes.update(json.loads(record['kit_code']))
        if record['consumables'] and record['consumables'] != '[]': consumables.update(json.loads(record['consumables']))
        if record['sample_type'] and record['sample_type'] != '[]': sample_types.update(json.loads(record['sample_type']))
        
    response_data = dict(records[0])
    response_data['kit_codes'] = sorted(list(kit_codes))
    response_data['consumables'] = sorted(list(consumables))
    response_data['sample_types'] = sorted(list(sample_types))
    return jsonify(response_data)

@app.route('/api/checklists', methods=['GET'])
def get_checklists():
    """Reads the generated checklist JSON file."""
    try:
        with open(CHECKLIST_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": f"Checklist data file '{CHECKLIST_DATA_FILE}' not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/requests', methods=['GET', 'POST'])
def handle_requests():
    """
    Handles requests for the IFU requests queue.
    - GET: Fetches a list of all requests.
    - POST: Creates a new request.
    """
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.get_json()
        created_by = data.get('created_by', 'System')
        if 'displayName' in data.get('user', {}):
             created_by = data['user']['displayName']
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ifu_requests (
                request_type, status, part_number_to_update, sample_type, 
                biomarkers, stability_period, consumables, market, 
                created_by, created_at, jira_key, request_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('request_type'), 'Pending Content Review', data.get('part_number_to_update'),
            data.get('sample_type'), data.get('biomarkers'), data.get('stability_period'),
            data.get('consumables'), data.get('market'), created_by, datetime.now(),
            data.get('jira_key'), data.get('request_summary')
        ))
        conn.commit()
        conn.close()
        print(f"A new IFU request was created by {created_by}.")
        return jsonify({"message": "Request created successfully"}), 201
    
    if request.method == 'GET':
        requests_from_db = conn.execute('SELECT * FROM ifu_requests ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in requests_from_db])

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Searches content panels for a given keyword using SQL LIKE.
    """
    data = request.get_json()
    search_term = data.get('searchTerm')
    if not search_term:
        return jsonify({"error": "Missing search term"}), 400
    conn = get_db_connection()
    query_param = f'%{search_term}%'
    search_results = conn.execute('''
        SELECT p.content_text, p.panel_type, d.part_number, d.document_version
        FROM content_panels p
        JOIN ifu_documents d ON p.document_id = d.id
        WHERE p.content_text LIKE ?
    ''', (query_param,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in search_results])
    
@app.route('/api/approve', methods=['POST'])
def approve_checklist():
    """Logs a checklist approval."""
    data = request.get_json()
    user_name = data.get('user_name', 'Unknown User')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO approval_log (part_number, document_version, approved_by, approved_at) VALUES (?, ?, ?, ?)',
                   (data.get('part_number'), data.get('revision_number'), user_name, datetime.now()))
    conn.commit()
    conn.close()
    print(f"Approval logged for {data.get('part_number')} by {user_name}")
    return jsonify({"message": "Approval logged"}), 201

@app.route('/api/compare', methods=['POST'])
def compare_content():
    """Performs sophisticated text comparison with filtering."""
    data = request.get_json()
    source_text = data.get('text')
    panel_type = data.get('panel_type')
    if not source_text or not panel_type:
        return jsonify({"error": "Missing text or panel_type"}), 400
    conn = get_db_connection()
    base_query = "SELECT d.part_number, d.document_version, d.language, p.content_text FROM ifu_documents d JOIN content_panels p ON d.id = p.document_id WHERE p.panel_type = ?"
    params = [panel_type]
    all_panels_to_compare = conn.execute(base_query, tuple(params)).fetchall()
    conn.close()
    results = []
    source_words = source_text.split()
    for row in all_panels_to_compare:
        target_words = row['content_text'].split()
        matcher = difflib.SequenceMatcher(None, source_words, target_words, autojunk=False)
        if 0.3 < matcher.ratio() < 0.999:
            results.append({
                "part_number": row['part_number'], "document_version": row['document_version'], "language": row['language'],
                "similarity": round(matcher.ratio(), 4), "opcodes": matcher.get_opcodes(), "comparison_text": row['content_text']
            })
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return jsonify(results)

# --- NEW ENDPOINT FOR DRAFTS ---
@app.route('/api/drafts', methods=['GET', 'POST'])
def handle_drafts():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.get_json()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO content_drafts (
                request_id, status, created_by, created_at, content_panels, 
                jira_key, request_summary, market, sample_type, consumables
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('request_id'), 'Pending Regulatory Review', 'Cintia (Content Team)',
            datetime.now(), json.dumps(data.get('content_panels')),
            data.get('jira_key'), data.get('request_summary'),
            data.get('market'), data.get('sample_type'), data.get('consumables')
        ))
        conn.commit()
        conn.close()
        return jsonify({"message": "Draft submitted for review successfully"}), 201

    if request.method == 'GET':
        query = "SELECT * FROM content_drafts WHERE status = 'Pending Regulatory Review' ORDER BY created_at DESC"
        drafts = conn.execute(query).fetchall()
        conn.close()
        results = []
        for row in drafts:
            draft = dict(row)
            draft['content_panels'] = json.loads(draft['content_panels']) if draft.get('content_panels') else []
            results.append(draft)
        return jsonify(results)

@app.route('/api/drafts/<int:draft_id>/approve', methods=['POST'])
def approve_draft(draft_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE content_drafts SET status = ? WHERE draft_id = ?", ('Approved', draft_id))
        conn.commit()
        if cursor.rowcount == 0:
             return jsonify({"error": "Draft not found"}), 404
        print(f"Draft #{draft_id} has been approved.")
        return jsonify({"message": f"Draft {draft_id} approved successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error during approval: {e}")
        return jsonify({"error": "A database error occurred"}), 500
    finally:
        conn.close()

# --- NEW ENDPOINT FOR SURFACING BOM DATA THROUGHOUT WORKFLOW ---

@app.route('/api/requests', methods=['GET'])
def get_all_requests():
    """
    Fetches all records from the ifu_requests table.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch all requests, ordering by the most recent first
        cursor.execute("SELECT * FROM ifu_requests ORDER BY created_at DESC")
        
        requests = cursor.fetchall()
        conn.close()
        
        # Convert the list of Row objects to a list of dictionaries
        return jsonify([dict(row) for row in requests]), 200

    except Exception as e:
        print(f"ERROR fetching requests: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/ifu_contents/search')
def search_ifu_contents():
    """
    Searches the ifu_contents table based on a query parameter 'q'.
    The search is performed against the 'part_number' column.
    """
    query_param = request.args.get('q', '')
    
    if not query_param:
        return jsonify([]) # Return empty list if no query is provided

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use a LIKE query to find matching part numbers
        search_term = f"%{query_param}%"
        cursor.execute(
            "SELECT * FROM ifu_contents WHERE part_number LIKE ?", 
            (search_term,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert list of Row objects to a list of dictionaries
        return jsonify([dict(row) for row in results])

    except Exception as e:
        print(f"ERROR during content search: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500        


# --- Dynamic dropdown data endpoints ---
@app.route('/api/structured-sample-types', methods=['GET'])
def get_structured_sample_types():
    conn = get_db_connection()
    rows = conn.execute("SELECT sample_type FROM ifu_documents WHERE sample_type IS NOT NULL").fetchall()
    conn.close()
    structured_types = defaultdict(set)
    for row in rows:
        try:
            types = json.loads(row['sample_type'])
            if len(types) > 1: structured_types[types[0]].add(types[1])
            elif len(types) == 1: structured_types[types[0]].add("General")
        except: structured_types[str(row['sample_type'])].add("General")
    for key in structured_types: structured_types[key] = sorted(list(structured_types[key]))
    return jsonify(structured_types)

@app.route('/api/consumables', methods=['GET'])
def get_consumables():
    conn = get_db_connection()
    rows = conn.execute('SELECT DISTINCT consumables FROM ifu_documents WHERE consumables IS NOT NULL').fetchall()
    conn.close()
    unique_consumables = set()
    for row in rows:
        try:
            items = json.loads(row['consumables'])
            for item in items: unique_consumables.add(item.strip())
        except: pass
    return jsonify(sorted(list(unique_consumables)))

    
    conn.commit()
    
    # Check if the update was successful
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Draft not found or already updated"}), 404
        
    conn.close()
    print(f"Draft #{draft_id} has been approved.")
    return jsonify({"message": f"Draft {draft_id} approved successfully"}), 200

# --- 5. Frontend serving ---

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serves the frontend application."""
    if path != "" and os.path.exists(os.path.join("static", path)):
        return send_from_directory('static', path)
    else:
        return send_from_directory('static', 'index.html')

# --- 6. Webhook Receivers --- #
    
@app.route('/api/webhook/jira', methods=['POST'])
def jira_webhook():
    """
    Listens for Jira webhooks, parses the data including all BOM fields,
    and creates a new request in the ifu_requests table.
    """
    try:
        # --- Start of Corrected Code ---

        # 1. Extract data from the nested JSON payload
        data = request.get_json()
        issue_data = data.get('issue', {})
        issue_fields = issue_data.get('fields', {})
        creator_name = issue_fields.get('creator', {}).get('displayName', 'Unknown User')
        created_timestamp = datetime.now() 

        # 2. Prepare the values tuple for the database
        # The order here MUST match the columns in the INSERT statement below
        db_values = (
    issue_fields.get('summary'),
    'New IFU',  # request_type
    issue_fields.get('issuetype', {}).get('name'),
    issue_fields.get('project', {}).get('name'),
    issue_fields.get('description'),
    issue_fields.get('customfield_10016'),  # Market
    issue_fields.get('customfield_10017'),  # Sample Type
    issue_fields.get('customfield_10018'),  # Consumables
    issue_fields.get('customfield_10019'),  # Kit Name
    issue_fields.get('customfield_10020'),  # Dispatch Codes
    issue_fields.get('customfield_10021'),  # Kit Codes
    issue_fields.get('customfield_10022'),  # KPA Specimen Bag
    issue_data.get('key'),                  # jira_key
    'Pending Content Review',               # status
    creator_name,                           # created_by
    created_timestamp                       # created_at
)

        # 3. Connect to DB and execute the corrected INSERT statement
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
    INSERT INTO ifu_requests (
        summary, request_type, issuetype, project, description, customfield_10016, 
        customfield_10017, customfield_10018, customfield_10019, 
        customfield_10020, customfield_10021, customfield_10022, 
        jira_key, status, created_by, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', db_values)

        conn.commit()
        conn.close()

        # --- End of Corrected Code ---

        print(f"Successfully processed webhook for Jira ticket {issue_data.get('key')}.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"ERROR processing webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
    
# --- 7. Main Execution Block ---
if __name__ == '__main__':
    print("Starting Flask server for Stitch...")
    app.run(debug=True, port=5001)