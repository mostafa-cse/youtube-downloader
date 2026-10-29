from flask import Flask, render_template, request, jsonify, send_file
import os, uuid, subprocess, threading, platform
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass
from utils import list_video_files, pick_folder as native_pick_folder
import downloader

app = Flask(__name__)
CURRENT_DIR = os.path.realpath(os.path.expanduser('~/Downloads'))
try:
    os.makedirs(CURRENT_DIR, exist_ok=True)
except Exception:
    pass
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
        try:
            chosen = native_pick_folder()
            if chosen and os.path.isdir(chosen):
                result['folder'] = chosen
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
    return jsonify({'dir': CURRENT_DIR, 'system': platform.system()})

@app.route('/get-system-info')
def get_system_info():
    sys_name = platform.system()
    default_browser = 'safari' if sys_name == 'Darwin' else 'chrome'
    return jsonify({
        'dir': CURRENT_DIR,
        'system': sys_name,
        'default_browser': default_browser
    })

@app.route('/download', methods=['POST'])
def start_download():
    global CURRENT_DIR
    data     = request.json or {}
    url      = data.get('url', '').strip()
    save_dir = data.get('folder') or CURRENT_DIR
    if save_dir:
        CURRENT_DIR = save_dir
    sys_name = platform.system()
    default_browser = 'safari' if sys_name == 'Darwin' else 'chrome'
    browser  = data.get('browser') or default_browser
    quality  = data.get('quality', 'best')
    filetype = data.get('filetype', 'mp4')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
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
    # Filter out cleared files using normalized path (normcase handles Windows case insensitivity)
    files  = [f for f in files if os.path.normcase(os.path.normpath(os.path.join(folder, f))) not in _hidden_files]
    return jsonify(files)

@app.route('/clear-history', methods=['POST'])
def clear_history():
    data = request.json or {}
    folder = data.get('folder', CURRENT_DIR) or CURRENT_DIR
    files  = list_video_files(folder)
    for f in files:
        _hidden_files.add(os.path.normcase(os.path.normpath(os.path.join(folder, f))))
    return jsonify({'success': True, 'cleared': len(files)})

@app.route('/open-file')
def open_file():
    p = request.args.get('path', '')
    if p:
        p = os.path.normpath(p)
        if os.path.exists(p):
            try:
                system = platform.system()
                if system == 'Darwin':
                    subprocess.Popen(['open', p])
                elif system == 'Windows':
                    os.startfile(p)
                else:
                    # Linux / Unix
                    subprocess.Popen(['xdg-open', p])
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': 'File not found'})

@app.route('/get-file')
def get_file():
    path = request.args.get('path', '')
    if path:
        norm = os.path.normpath(path)
        exts = {'.mp4', '.mkv', '.mp3', '.m4a', '.aac', '.webm', '.mov', '.flv'}
        if os.path.isfile(norm) and os.path.splitext(norm)[1].lower() in exts:
            return send_file(norm, as_attachment=True)
    return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=False, port=5001)
