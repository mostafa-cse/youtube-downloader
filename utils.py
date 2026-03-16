import os, subprocess

def pick_folder_mac():
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

def _height_steps(quality):
    q = (quality or 'best').lower()
    if q == '1080p':
        return [1080, 720, 480, 360, 240]
    if q == '720p':
        return [720, 480, 360, 240]
    if q == '480p':
        return [480, 360, 240]
    if q == '360p':
        return [360, 240]
    if q == '240p':
        return [240]
    return [2160, 1440, 1080, 720, 480, 360, 240]

def _video_selector_ladder(quality, filetype):
    heights = _height_steps(quality)
    selectors = []

    for h in heights:
        selectors += [
            f'bestvideo[height<={h}]+bestaudio/best[height<={h}]',
            f'bv*[height<={h}]+ba/b[height<={h}]',
        ]
        if filetype == 'mp4':
            selectors += [
                f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}]',
                f'bestvideo[height<={h}][ext=mp4]+bestaudio/best[height<={h}]',
            ]

    selectors += [
        'bestvideo+bestaudio/best',
        'bv*+ba/best',
        'best'
    ]

    seen = set()
    result = []
    for s in selectors:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result

def _audio_selector_ladder(filetype):
    if filetype == 'm4a':
        return ['bestaudio[ext=m4a]/bestaudio', 'bestaudio', 'best']
    return ['bestaudio/best', 'best']

def get_format_opts(quality, filetype):
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
    opts = {
        'format': selectors[0],
        'format_sort': ['res', 'fps', 'hdr', 'vcodec', 'acodec', 'br', 'size']
    }
    if filetype == 'mp4':
        opts['merge_output_format'] = 'mp4'
    elif filetype == 'mkv':
        opts['merge_output_format'] = 'mkv'
    return opts

def get_format_ladder(quality, filetype):
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'aac'
        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': '320'}]
        return [({'format': sel, 'postprocessors': pp}) for sel in _audio_selector_ladder(filetype)]

    extra = {
        'format_sort': ['res', 'fps', 'hdr', 'vcodec', 'acodec', 'br', 'size']
    }
    if filetype == 'mp4':
        extra['merge_output_format'] = 'mp4'
    elif filetype == 'mkv':
        extra['merge_output_format'] = 'mkv'

    result = []
    for sel in _video_selector_ladder(quality, filetype):
        d = {'format': sel}
        d.update(extra)
        result.append(d)
    return result
