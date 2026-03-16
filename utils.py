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

# ── Format selector ladder ───────────────────────────────────────────────────
# Each entry is tried in order; the first one that succeeds is used.
# This avoids the hard "Requested format is not available" error.

def _video_selector_ladder(quality, filetype):
    """
    Returns a list of yt-dlp format selector strings, from most specific
    to most permissive.  The caller retries until one succeeds.
    """
    height_map = {
        'best':  None,
        '4k':    2160,
        '1080p': 1080,
        '720p':  720,
        '480p':  480,
        '360p':  360,
    }
    max_h = height_map.get(quality.lower())
    h = f'[height<={max_h}]' if max_h else ''

    if filetype == 'mp4':
        return [
            f'bestvideo{h}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{h}[ext=mp4]+bestaudio',
            f'bestvideo{h}+bestaudio/bestvideo{h}',
            f'best{h}[ext=mp4]',
            f'best{h}',
            'bestvideo+bestaudio/best',
            'best',
        ]
    else:  # mkv or any other container
        return [
            f'bestvideo{h}+bestaudio/bestvideo{h}',
            f'best{h}',
            'bestvideo+bestaudio/best',
            'best',
        ]

def _audio_selector_ladder(filetype):
    if filetype == 'm4a':
        return ['bestaudio[ext=m4a]/bestaudio', 'best']
    # mp3
    return ['bestaudio/best', 'best']

def get_format_opts(quality, filetype):
    """Return the first ydl_opts dict in the fallback ladder (for initial attempt)."""
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'aac'
        return {
            'format': _audio_selector_ladder(filetype)[0],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '320',
            }]
        }

    selectors = _video_selector_ladder(quality, filetype)
    opts = {'format': selectors[0]}
    if filetype == 'mp4':
        opts['merge_output_format'] = 'mp4'
    elif filetype == 'mkv':
        opts['merge_output_format'] = 'mkv'
    return opts

def get_format_ladder(quality, filetype):
    """Return the full list of (format_str, extra_opts) tuples for fallback retry."""
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'aac'
        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': '320'}]
        return [({'format': sel, 'postprocessors': pp}) for sel in _audio_selector_ladder(filetype)]

    extra = {}
    if filetype == 'mp4':
        extra = {'merge_output_format': 'mp4'}
    elif filetype == 'mkv':
        extra = {'merge_output_format': 'mkv'}

    result = []
    for sel in _video_selector_ladder(quality, filetype):
        d = {'format': sel}
        d.update(extra)
        result.append(d)
    return result
