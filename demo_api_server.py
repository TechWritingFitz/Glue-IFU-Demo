import json
import os
import difflib
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict

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

# --- Mock Data (replaces database) ---
mock_ifu_documents = [
    {"id": 1, "part_number": "LGC-001", "document_version": "v1.2", "language": "EN", 
     "sample_type": '["Blood", "Serum"]', "kit_code": '["KIT001", "KIT002"]', 
     "consumables": '["Test Tube", "Lancet", "Collection Card"]', "market": "US"},
    {"id": 2, "part_number": "LGC-002", "document_version": "v1.1", "language": "EN",
     "sample_type": '["Saliva"]', "kit_code": '["KIT003"]', 
     "consumables": '["Saliva Tube", "Funnel"]', "market": "EU"},
    {"id": 3, "part_number": "LGC-003", "document_version": "v2.0", "language": "EN",
     "sample_type": '["Urine"]', "kit_code": '["KIT004"]', 
     "consumables": '["Urine Cup", "Preservative"]', "market": "Global"}
]

mock_content_panels = [
    {"id": 1, "document_id": 1, "panel_number": 1, "panel_type": "instructions", 
     "content_text": "Wash your hands thoroughly with soap and water before handling the test kit. Ensure all materials are at room temperature."},
    {"id": 2, "document_id": 1, "panel_number": 2, "panel_type": "warnings", 
     "content_text": "For in vitro diagnostic use only. Do not use if package is damaged or expired."},
    {"id": 3, "document_id": 1, "panel_number": 3, "panel_type": "collection", 
     "content_text": "Use the provided lancet to prick your finger. Allow blood to drop onto the collection card until all circles are filled."},
    {"id": 4, "document_id": 2, "panel_number": 1, "panel_type": "instructions", 
     "content_text": "Collect saliva sample first thing in the morning before eating, drinking, or brushing teeth."},
    {"id": 5, "document_id": 2, "panel_number": 2, "panel_type": "warnings", 
     "content_text": "For in vitro diagnostic use only. Keep away from children. Store at room temperature."},
    {"id": 6, "document_id": 3, "panel_number": 1, "panel_type": "collection", 
     "content_text": "Collect first morning urine in the provided sterile container. Fill to the marked line."},
]

mock_requests = [
    {"request_id": 1, "request_type": "New IFU", "status": "Pending Content Review", 
     "jira_key": "NPI-123", "request_summary": "Create IFU for new cholesterol test kit",
     "sample_type": "Blood", "market": "US", "created_by": "John Smith", 
     "created_at": "2025-07-29T10:30:00"},
    {"request_id": 2, "request_type": "Update IFU", "status": "In Progress", 
     "jira_key": "NPI-124", "request_summary": "Update warnings for diabetes kit",
     "sample_type": "Urine", "market": "EU", "created_by": "Sarah Johnson", 
     "created_at": "2025-07-28T14:15:00"}
]

mock_drafts = [
    {"draft_id": 1, "request_id": 1, "status": "Pending Regulatory Review", 
     "created_by": "Cintia (Content Team)", "jira_key": "NPI-123",
     "request_summary": "Create IFU for new cholesterol test kit",
     "content_panels": '[{"panel_type": "instructions", "content": "Sample instruction content"}]',
     "created_at": "2025-07-30T09:00:00"}
]

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Helper Functions ---
def find_document_by_id(doc_id):
    return next((doc for doc in mock_ifu_documents if doc['id'] == doc_id), None)

def find_panels_by_document_id(doc_id):
    return [panel for panel in mock_content_panels if panel['document_id'] == doc_id]

# --- API Endpoints ---

@app.route('/api/ifus', methods=['GET'])
def get_all_ifus():
    """Endpoint to fetch a list of all unique IFU documents, including ID."""
    return jsonify(mock_ifu_documents)

@app.route('/api/ifu/<int:document_id>', methods=['GET'])
def get_ifu_details(document_id):
    """Endpoint to fetch all content panels for a single IFU document."""
    panels = find_panels_by_document_id(document_id)
    if not panels:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(panels)
    
@app.route('/api/ifu-by-part-number/<string:part_number>/<string:doc_version>', methods=['GET'])
def get_ifu_by_part_number(part_number, doc_version):
    """Fetches all enriched metadata for a specific IFU part_number and version."""
    record = next((doc for doc in mock_ifu_documents 
                  if doc['part_number'] == part_number and doc['document_version'] == doc_version), None)
    
    if not record:
        return jsonify({"error": "IFU not found"}), 404
    
    # Parse JSON fields
    response_data = record.copy()
    response_data['kit_codes'] = json.loads(record.get('kit_code', '[]'))
    response_data['consumables'] = json.loads(record.get('consumables', '[]'))
    response_data['sample_types'] = json.loads(record.get('sample_type', '[]'))
    
    return jsonify(response_data)

@app.route('/api/checklists', methods=['GET'])
def get_checklists():
    """Returns mock checklist data."""
    mock_checklist = {
        "checklists": [
            {"id": 1, "name": "Standard IFU Checklist", "items": [
                "Instructions are clear and concise",
                "All warnings are present",
                "Collection procedures are accurate"
            ]}
        ]
    }
    return jsonify(mock_checklist)

@app.route('/api/requests', methods=['GET', 'POST'])
def handle_requests():
    """
    Handles requests for the IFU requests queue.
    - GET: Fetches a list of all requests.
    - POST: Creates a new request.
    """
    if request.method == 'POST':
        data = request.get_json()
        created_by = data.get('created_by', 'System')
        if 'displayName' in data.get('user', {}):
             created_by = data['user']['displayName']
        
        new_request = {
            "request_id": len(mock_requests) + 1,
            "request_type": data.get('request_type'),
            "status": 'Pending Content Review',
            "part_number_to_update": data.get('part_number_to_update'),
            "sample_type": data.get('sample_type'),
            "biomarkers": data.get('biomarkers'),
            "stability_period": data.get('stability_period'),
            "consumables": data.get('consumables'),
            "market": data.get('market'),
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "jira_key": data.get('jira_key'),
            "request_summary": data.get('request_summary')
        }
        mock_requests.append(new_request)
        
        print(f"A new IFU request was created by {created_by}.")
        return jsonify({"message": "Request created successfully"}), 201
    
    return jsonify(mock_requests)

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Searches content panels for a given keyword using simple text matching.
    """
    data = request.get_json()
    search_term = data.get('searchTerm', '').lower()
    if not search_term:
        return jsonify({"error": "Missing search term"}), 400
    
    results = []
    for panel in mock_content_panels:
        if search_term in panel['content_text'].lower():
            # Find the document for this panel
            doc = find_document_by_id(panel['document_id'])
            if doc:
                results.append({
                    "content_text": panel['content_text'],
                    "panel_type": panel['panel_type'],
                    "part_number": doc['part_number'],
                    "document_version": doc['document_version']
                })
    
    return jsonify(results)
    
@app.route('/api/approve', methods=['POST'])
def approve_checklist():
    """Logs a checklist approval."""
    data = request.get_json()
    user_name = data.get('user_name', 'Unknown User')
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
    
    # Find panels of the same type
    matching_panels = [panel for panel in mock_content_panels if panel['panel_type'] == panel_type]
    
    results = []
    source_words = source_text.split()
    
    for panel in matching_panels:
        # Find the document for this panel
        doc = find_document_by_id(panel['document_id'])
        if not doc:
            continue
            
        target_words = panel['content_text'].split()
        matcher = difflib.SequenceMatcher(None, source_words, target_words, autojunk=False)
        
        if 0.3 < matcher.ratio() < 0.999:
            results.append({
                "part_number": doc['part_number'],
                "document_version": doc['document_version'],
                "language": doc['language'],
                "similarity": round(matcher.ratio(), 4),
                "opcodes": matcher.get_opcodes(),
                "comparison_text": panel['content_text']
            })
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return jsonify(results)

@app.route('/api/drafts', methods=['GET', 'POST'])
def handle_drafts():
    if request.method == 'POST':
        data = request.get_json()
        new_draft = {
            "draft_id": len(mock_drafts) + 1,
            "request_id": data.get('request_id'),
            "status": 'Pending Regulatory Review',
            "created_by": 'Cintia (Content Team)',
            "created_at": datetime.now().isoformat(),
            "content_panels": json.dumps(data.get('content_panels')),
            "jira_key": data.get('jira_key'),
            "request_summary": data.get('request_summary'),
            "market": data.get('market'),
            "sample_type": data.get('sample_type'),
            "consumables": data.get('consumables')
        }
        mock_drafts.append(new_draft)
        return jsonify({"message": "Draft submitted for review successfully"}), 201

    # GET request
    results = []
    for row in mock_drafts:
        if row['status'] == 'Pending Regulatory Review':
            draft = row.copy()
            draft['content_panels'] = json.loads(draft.get('content_panels', '[]'))
            results.append(draft)
    return jsonify(results)

@app.route('/api/drafts/<int:draft_id>/approve', methods=['POST'])
def approve_draft(draft_id):
    draft = next((d for d in mock_drafts if d['draft_id'] == draft_id), None)
    if not draft:
        return jsonify({"error": "Draft not found"}), 404
    
    draft['status'] = 'Approved'
    print(f"Draft #{draft_id} has been approved.")
    return jsonify({"message": f"Draft {draft_id} approved successfully"}), 200

@app.route('/api/ifu_contents/search')
def search_ifu_contents():
    """
    Searches the mock IFU contents based on part_number.
    """
    query_param = request.args.get('q', '').lower()
    
    if not query_param:
        return jsonify([])

    results = [doc for doc in mock_ifu_documents 
              if query_param in doc['part_number'].lower()]
    return jsonify(results)

@app.route('/api/structured-sample-types', methods=['GET'])
def get_structured_sample_types():
    structured_types = defaultdict(set)
    for doc in mock_ifu_documents:
        try:
            types = json.loads(doc.get('sample_type', '[]'))
            if len(types) > 1:
                structured_types[types[0]].add(types[1])
            elif len(types) == 1:
                structured_types[types[0]].add("General")
        except:
            pass
    
    # Convert sets to sorted lists
    for key in structured_types:
        structured_types[key] = sorted(list(structured_types[key]))
    
    return jsonify(dict(structured_types))

@app.route('/api/consumables', methods=['GET'])
def get_consumables():
    unique_consumables = set()
    for doc in mock_ifu_documents:
        try:
            items = json.loads(doc.get('consumables', '[]'))
            for item in items:
                unique_consumables.add(item.strip())
        except:
            pass
    
    return jsonify(sorted(list(unique_consumables)))

@app.route('/api/webhook/jira', methods=['POST'])
def jira_webhook():
    """
    Simulated Jira webhook receiver.
    """
    try:
        data = request.get_json()
        issue_data = data.get('issue', {})
        issue_fields = issue_data.get('fields', {})
        creator_name = issue_fields.get('creator', {}).get('displayName', 'Unknown User')
        
        new_request = {
            "request_id": len(mock_requests) + 1,
            "summary": issue_fields.get('summary'),
            "request_type": 'New IFU',
            "issuetype": issue_fields.get('issuetype', {}).get('name'),
            "project": issue_fields.get('project', {}).get('name'),
            "description": issue_fields.get('description'),
            "customfield_10016": issue_fields.get('customfield_10016'),  # Market
            "jira_key": issue_data.get('key'),
            "status": 'Pending Content Review',
            "created_by": creator_name,
            "created_at": datetime.now().isoformat()
        }
        mock_requests.append(new_request)
        
        print(f"Successfully processed webhook for Jira ticket {issue_data.get('key')}.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"ERROR processing webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# --- Frontend serving ---
@app.route('/')
def index():
    return send_from_directory('STATIC', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('STATIC', filename)

@app.route('/<path:path>')
def serve(path):
    """Serves the frontend application."""
    if path != "" and os.path.exists(os.path.join("STATIC", path)):
        return send_from_directory('STATIC', path)
    else:
        return send_from_directory('STATIC', 'index.html')

# --- Main Execution Block ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting Flask server for Glue Demo...")
    app.run(debug=False, host='0.0.0.0', port=port)