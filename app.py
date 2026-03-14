from flask import Flask, render_template, request, jsonify, send_file
import os, uuid
from utils import pick_folder_mac, list_video_files
import downloader

app = Flask(__name__)
CURRENT_DIR = os.path.expanduser('~/Downloads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pick-folder', methods=['POST'])
def pick_folder():
    global CURRENT_DIR
    folder = pick_folder_mac()
    if folder:
        CURRENT_DIR = folder
        return jsonify({'folder': folder, 'success': True})
    return jsonify({'folder': None, 'success': False})

@app.route('/get-dir')
def get_dir():
    return jsonify({'dir': CURRENT_DIR})

@app.route('/download', methods=['POST'])
def start_download():
    global CURRENT_DIR
    data     = request.json
    url      = data.get('url', '').strip()
    save_dir = data.get('folder') or CURRENT_DIR
    browser  = data.get('browser', 'safari')
    quality  = data.get('quality', 'best')
    filetype = data.get('filetype', 'mp4')
    CURRENT_DIR = save_dir
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    tid = str(uuid.uuid4())
    downloader.tasks[tid] = {'status': 'queued', 'log': [], 'progress': 0}
    downloader.start(tid, url, save_dir, browser, quality, filetype)
    return jsonify({'task_id': tid})

@app.route('/status/<tid>')
def get_status(tid):
    return jsonify(downloader.tasks.get(tid, {'status': 'not_found', 'log': []}))

@app.route('/files')
def list_files():
    folder = request.args.get('folder', CURRENT_DIR)
    return jsonify(list_video_files(folder))

@app.route('/get-file')
def get_file():
    path = request.args.get('path', '')
    if path and os.path.isfile(path):
        return send_file(path, as_attachment=True)
    return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=False, port=5001)
