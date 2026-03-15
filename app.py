from flask import Flask, render_template, request, jsonify, send_file
import os, uuid, subprocess, threading
from utils import list_video_files
import downloader

app = Flask(__name__)
CURRENT_DIR = os.path.expanduser('~/Downloads')
_hidden_files = set()  # tracks cleared files

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pick-folder', methods=['POST'])
def pick_folder():
    global CURRENT_DIR
    result = {'folder': None}
    done   = threading.Event()

    def _pick():
        script = '''tell application "Finder"
    activate
    set chosen to choose folder with prompt "Select download folder"
    return POSIX path of chosen
end tell'''
        try:
            out = subprocess.check_output(
                ['osascript', '-e', script],
                stderr=subprocess.DEVNULL, timeout=60
            )
            result['folder'] = out.decode().strip()
        except Exception:
            pass
        done.set()

    t = threading.Thread(target=_pick)
    t.daemon = True
    t.start()
    done.wait(timeout=65)

    if result['folder']:
        CURRENT_DIR = result['folder']
        return jsonify({'folder': result['folder'], 'success': True})
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
    if save_dir:
        CURRENT_DIR = save_dir
    browser  = data.get('browser', 'safari')
    quality  = data.get('quality', 'best')
    filetype = data.get('filetype', 'mp4')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    tid = str(uuid.uuid4())
    downloader.tasks[tid] = {'status': 'queued', 'log': [], 'progress': 0}
    downloader.start(tid, url, save_dir, browser, quality, filetype)
    return jsonify({'task_id': tid})

@app.route('/cancel/<tid>', methods=['POST'])
def cancel_download(tid):
    if tid in downloader.tasks:
        downloader.tasks[tid]['cancel'] = True
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/status/<tid>')
def get_status(tid):
    return jsonify(downloader.tasks.get(tid, {'status': 'not_found', 'log': []}))

@app.route('/files')
def list_files():
    folder = request.args.get('folder', CURRENT_DIR) or CURRENT_DIR
    files  = list_video_files(folder)
    # Filter out cleared files
    files  = [f for f in files if (folder + '/' + f) not in _hidden_files]
    return jsonify(files)

@app.route('/clear-history', methods=['POST'])
def clear_history():
    folder = request.json.get('folder', CURRENT_DIR) or CURRENT_DIR
    files  = list_video_files(folder)
    for f in files:
        _hidden_files.add(folder + '/' + f)
    return jsonify({'success': True, 'cleared': len(files)})

@app.route('/open-file')
def open_file():
    p = request.args.get('path', '')
    if p and os.path.exists(p):
        subprocess.Popen(['open', p])
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'File not found'})

@app.route('/get-file')
def get_file():
    path = request.args.get('path', '')
    if path and os.path.isfile(path):
        return send_file(path, as_attachment=True)
    return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=False, port=5001)
