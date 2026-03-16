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

def _max_height(quality):
    q = (quality or 'best').lower().replace('p','').strip()
    return {'best':None,'4k':2160,'2160':2160,'1440':1440,
            '1080':1080,'720':720,'480':480,'360':360,'240':240}.get(q)

def _video_selector_ladder(quality, filetype):
    max_h = _max_height(quality)
    h = f'[height<={max_h}]' if max_h else ''
    steps = [h2 for h2 in [1080,720,480,360,240]
             if (not max_h or h2 <= max_h)]
    ladder = [
        f'bestvideo{h}+bestaudio/best{h}',
        f'bestvideo{h}[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo{h}+bestaudio/best{h}',
    ]
    for s in steps:
        ladder += [f'bestvideo[height<={s}]+bestaudio/best[height<={s}]']
    ladder += ['bestvideo+bestaudio/best', 'best']
    seen, result = set(), []
    for x in ladder:
        if x not in seen: seen.add(x); result.append(x)
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
        'format_sort': ['res:2160', 'fps', 'hdr:12', 'vcodec', 'acodec', 'br'],
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
