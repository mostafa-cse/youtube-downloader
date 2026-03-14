import subprocess, os, shutil

def pick_folder_mac():
    script = 'POSIX path of (choose folder with prompt "Select Download Folder:")'
    r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None

def list_video_files(folder):
    if not folder or not os.path.exists(folder):
        return []
    exts = ('.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.opus')
    return sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(exts) and not f.startswith('.')
    ])

def get_ffmpeg_path():
    # static_ffmpeg puts it on PATH, shutil.which finds it
    return shutil.which('ffmpeg')

def get_format_opts(quality, filetype):
    ffmpeg = get_ffmpeg_path()
    height_map = {'4k':'2160','1080':'1080','720':'720','480':'480','360':'360','240':'240'}

    if filetype == 'mp3':
        opts = {'format': 'bestaudio/best'}
        if ffmpeg:
            opts['postprocessors'] = [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'320'}]
            opts['ffmpeg_location'] = ffmpeg
        return opts

    if filetype == 'm4a':
        opts = {'format': 'bestaudio[ext=m4a]/bestaudio/best'}
        if ffmpeg:
            opts['postprocessors'] = [{'key':'FFmpegExtractAudio','preferredcodec':'m4a'}]
            opts['ffmpeg_location'] = ffmpeg
        return opts

    merge = 'mkv' if filetype == 'mkv' else 'mp4'
    if ffmpeg:
        if quality in height_map:
            h = height_map[quality]
            fmt = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]'
        else:
            fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        return {'format': fmt, 'merge_output_format': merge, 'ffmpeg_location': ffmpeg}
    else:
        h = height_map.get(quality, '')
        fmt = f'best[height<={h}][ext=mp4]/best[height<={h}]/best' if h else 'best[ext=mp4]/best'
        return {'format': fmt}
