from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('STATIC', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('STATIC', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)