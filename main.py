import sys, os, time, threading, urllib.request

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()   # injects ffmpeg into PATH from venv — no brew needed
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))
from app import app

DEFAULT_PORT = int(os.environ.get('PORT', 5001))

def run_flask(port=DEFAULT_PORT):
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

def wait_for_flask(url=None, timeout=10):
    if url is None:
        url = f'http://127.0.0.1:{DEFAULT_PORT}/'
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.05)
    return False

def main():
    port = DEFAULT_PORT
    server_mode = any(arg in sys.argv for arg in ('--server', '--no-gui', '-s'))
    
    # On Linux without DISPLAY, or if server flag is passed, run in web server mode
    if server_mode or (not os.environ.get('DISPLAY') and sys.platform.startswith('linux')):
        print(f"Starting YT Downloader server on http://127.0.0.1:{port} ...")
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
        return

    try:
        import webview
    except ImportError:
        print(f"pywebview not found. Running in server mode at http://127.0.0.1:{port} ...")
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
        return

    t = threading.Thread(target=run_flask, args=(port,), daemon=True)
    t.start()
    
    if not wait_for_flask(timeout=10):
        print(f"Error: Flask server failed to start on port {port} within 10 seconds.")
        sys.exit(1)
        
    try:
        webview.create_window(
            'YT Downloader',
            f'http://127.0.0.1:{port}',
            width=960, height=760,
            min_size=(680, 560),
            resizable=True,
            text_select=True
        )
        webview.start()
    except Exception as e:
        print(f"Native GUI window unavailable ({e}).")
        print(f"Opening YT Downloader in your default browser at http://127.0.0.1:{port} ...")
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{port}')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down YT Downloader.")

if __name__ == '__main__':
    main()
