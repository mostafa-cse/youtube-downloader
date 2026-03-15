import os, subprocess

def pick_folder_mac():
    # Try Finder-based dialog first (works outside sandbox)
    script = '''
tell application "Finder"
    activate
    set chosen to choose folder with prompt "Select download folder"
    return POSIX path of chosen
end tell
'''
    try:
        out = subprocess.check_output(
            ['osascript', '-e', script],
            stderr=subprocess.DEVNULL,
            timeout=60
        )
        return out.decode().strip()
    except Exception:
        pass
    # Fallback: System Events
    script2 = 'tell app "System Events" to return POSIX path of (choose folder with prompt "Select download folder")'
    try:
        out = subprocess.check_output(
            ['osascript', '-e', script2],
            stderr=subprocess.DEVNULL,
            timeout=60
        )
        return out.decode().strip()
    except Exception:
        return None

def list_video_files(folder):
    exts = {'.mp4', '.mkv', '.mp3', '.m4a', '.webm', '.mov', '.flv'}
    try:
        files = [f for f in os.listdir(folder)
                 if os.path.splitext(f)[1].lower() in exts
                 and not f.startswith('.')]
        return sorted(files, key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
    except Exception:
        return []

def get_format_opts(quality, filetype):
    # ── Audio only ──────────────────────────────────────────────
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'aac'
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '320',
            }]
        }

    # ── Video: always include /best fallback so it never hard-fails ──
    fmt_map = {
        'best':  'bestvideo+bestaudio/best',
        '4k':    'bestvideo[height<=2160]+bestaudio/bestvideo[height<=2160]/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/bestvideo[height<=1080]/best',
        '720p':  'bestvideo[height<=720]+bestaudio/bestvideo[height<=720]/best',
        '480p':  'bestvideo[height<=480]+bestaudio/bestvideo[height<=480]/best',
        '360p':  'bestvideo[height<=360]+bestaudio/bestvideo[height<=360]/best',
    }

    fmt = fmt_map.get(quality.lower(), 'bestvideo+bestaudio/best')
    opts = {'format': fmt}

    if filetype == 'mp4':
        opts['merge_output_format'] = 'mp4'
    elif filetype == 'mkv':
        opts['merge_output_format'] = 'mkv'

    return opts
