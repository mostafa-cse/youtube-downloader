import os, subprocess, platform, shutil

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

def pick_folder_linux():
    if shutil.which('zenity'):
        try:
            out = subprocess.check_output(
                ['zenity', '--file-selection', '--directory', '--title=Select download folder'],
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            return out.decode().strip()
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            out = subprocess.check_output(
                ['kdialog', '--getexistingdirectory', '--title', 'Select download folder'],
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            return out.decode().strip()
        except Exception:
            pass
    return None

def pick_folder_windows():
    cmd = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$f = New-Object System.Windows.Forms.FolderBrowserDialog; '
        '$f.Description = "Select download folder"; '
        '$f.ShowNewFolderButton = $true; '
        'if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }'
    )
    try:
        out = subprocess.check_output(
            ['powershell', '-NoProfile', '-Sta', '-Command', cmd],
            stderr=subprocess.DEVNULL,
            timeout=60
        )
        return out.decode().strip()
    except Exception:
        return None

def pick_folder():
    system = platform.system()
    if system == 'Darwin':
        return pick_folder_mac()
    elif system == 'Windows':
        return pick_folder_windows()
    else:
        return pick_folder_linux()

def list_video_files(folder):
    exts = {'.mp4', '.mkv', '.mp3', '.m4a', '.aac', '.webm', '.mov', '.flv'}
    try:
        files = [f for f in os.listdir(folder)
                 if os.path.splitext(f)[1].lower() in exts
                 and not f.startswith('.')]
        return sorted(files, key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
    except Exception:
        return []

def _max_height(quality):
    q = (quality or 'best').lower().replace('p','').strip()
    return {'best':None,'8k':4320,'4320':4320,'4k':2160,'2160':2160,'1440':1440,
            '1080':1080,'720':720,'480':480,'360':360,'240':240,'144':144}.get(q)

def _video_selector_ladder(quality, filetype):
    max_h = _max_height(quality)
    h = f'[height<={max_h}]' if max_h else ''
    steps = [h2 for h2 in [4320, 2160, 1440, 1080, 720, 480, 360, 240]
             if (not max_h or h2 <= max_h)]
    if filetype == 'mp4':
        ladder = [
            # Preferred for MP4: Best video + AAC audio (avoids Opus audio playback issues on Mac & Windows)
            f'bestvideo{h}+bestaudio[acodec^=mp4a]/bestvideo{h}+bestaudio/best{h}',
            f'bestvideo{h}[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo{h}+bestaudio/best{h}',
        ]
        for s in steps:
            ladder += [
                f'bestvideo[height<={s}]+bestaudio[acodec^=mp4a]/bestvideo[height<={s}]+bestaudio/best[height<={s}]',
                f'bestvideo[height<={s}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={s}]',
            ]
        ladder += ['bestvideo+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best', 'best']
    else:
        ladder = [
            f'bestvideo{h}+bestaudio/best{h}',
            f'bestvideo{h}[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo{h}+bestaudio/best{h}',
        ]
        for s in steps:
            ladder += [
                f'bestvideo[height<={s}]+bestaudio/best[height<={s}]',
                f'bestvideo[height<={s}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={s}]',
            ]
        ladder += ['bestvideo+bestaudio/best', 'best']
    seen, result = set(), []
    for x in ladder:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result

def _audio_selector_ladder(filetype):
    if filetype == 'm4a':
        return ['bestaudio[ext=m4a]/bestaudio', 'bestaudio', 'best']
    return ['bestaudio/best', 'best']

def get_format_opts(quality, filetype):
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'm4a'
        return {
            'format': _audio_selector_ladder(filetype)[0],
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': '320',
                },
                {'key': 'FFmpegMetadata'},
            ]
        }

    selectors = _video_selector_ladder(quality, filetype)
    opts = {
        'format': selectors[0],
        'format_sort': ['res', 'fps', 'hdr', 'vcodec', 'acodec', 'br', 'size']
    }
    if filetype in ('mp4', 'mkv'):
        opts['merge_output_format'] = filetype
    return opts

def get_suggested_quality(info):
    """
    Returns optimal suggested quality based on available stream formats:
    - 1080p if available or higher (ideal balance of quality, size & merge speed)
    - Highest available if below 1080p (e.g. 720p or 480p)
    """
    if not info:
        return 'best'
    formats = info.get('formats', [])
    heights = sorted({f['height'] for f in formats if f.get('height') and f.get('vcodec') != 'none'}, reverse=True)
    if not heights:
        return 'best'
    if 1080 in heights or heights[0] >= 1080:
        return '1080'
    return str(heights[0])

def get_format_ladder(quality, filetype):
    if filetype in ('mp3', 'm4a'):
        codec = 'mp3' if filetype == 'mp3' else 'm4a'
        pp = [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': '320'},
            {'key': 'FFmpegMetadata'},
        ]
        return [({'format': sel, 'postprocessors': pp}) for sel in _audio_selector_ladder(filetype)]

    extra = {
        'format_sort': ['res', 'fps', 'hdr:12', 'vcodec', 'acodec', 'br'],
    }
    if filetype in ('mp4', 'mkv'):
        extra['merge_output_format'] = filetype

    result = []
    for sel in _video_selector_ladder(quality, filetype):
        d = {'format': sel}
        d.update(extra)
        result.append(d)
    return result
