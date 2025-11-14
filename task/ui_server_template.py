from flask import Flask, send_file, send_from_directory
import os

app = Flask(__name__)

OUTPUT_HTML_PATH = "{{output_html_path}}"
TASK_TEMPLATE_DIR = "{{task_template_dir}}"

@app.route('/')
def index():
    """Serve the generated output.html."""
    if os.path.exists(OUTPUT_HTML_PATH):
        return send_file(OUTPUT_HTML_PATH, mimetype='text/html')
    return "<h1>output.html not found</h1>", 404

@app.route('/task/template/<path:filename>')
def serve_template_files(filename):
    """Serve CSS and other template files."""
    return send_from_directory(TASK_TEMPLATE_DIR, filename)

if __name__ == '__main__':
    app.run(host='{{host}}', port={{port}}, debug=False)
