import static_ffmpeg
static_ffmpeg.add_paths()   # injects ffmpeg into PATH from venv — no brew needed

import webview, threading, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app

def run_flask():
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    import time; time.sleep(1.2)
    webview.create_window(
        'YT Downloader',
        'http://127.0.0.1:5001',
        width=960, height=760,
        min_size=(680, 560),
        resizable=True
    )
    webview.start()
