from flask import Flask, send_from_directory
import json
import os
import sys
sys.path.insert(0, '/app')
from task.OutputParser import OutputParser
from web.Builder import Builder

app = Flask(__name__)

TASK_TEMPLATE_DIR = "{{task_template_dir}}"
TASKS_CONFIG_PATH = "{{tasks_config_path}}"
VAR_DIR = "{{var_dir}}"
HOST = '{{host}}'
PORT = {{port}}

@app.route('/')
def index():
    """Generate and serve HTML dynamically."""
    try:
        if not os.path.exists(TASKS_CONFIG_PATH):
            return "<h1>Tasks configuration not found</h1>", 404
        with open(TASKS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            tasks_config = json.load(f)
        builder = Builder()
        output_parser = OutputParser()
        for task_data in tasks_config:
            task_name = task_data['name']
            html = output_parser.get_html(task_name)
            data = output_parser.get_json(task_name)
            if html or data:
                builder.add(task_name, {
                    'html': html,
                    'data': data,
                    'is_previous': False
                })
        html = builder.build()
        return html
    except Exception as e:
        return f"<h1>Error generating HTML</h1><p>{str(e)}</p>", 500

@app.route('/task/template/<path:filename>')
def serve_template_files(filename):
    """Serve CSS and other template files."""
    return send_from_directory(TASK_TEMPLATE_DIR, filename)

@app.route('/var/<path:filename>')
def serve_var_files(filename):
    """Serve files from var directory (thumbnails, frames, etc.)."""
    return send_from_directory(VAR_DIR, filename)

@app.route('/tmp/<path:filename>')
def serve_tmp_files(filename):
    """Serve files from tmp directory (thumbnail images, etc.)."""
    return send_from_directory('/tmp', filename)

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=False)
