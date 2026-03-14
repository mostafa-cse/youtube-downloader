import yt_dlp, os, threading
from datetime import datetime
from utils import get_format_opts

tasks = {}

def ts():
    return datetime.now().strftime('%H:%M:%S')

def log(tid, level, msg):
    tasks[tid]['log'].append({'time': ts(), 'level': level, 'msg': msg})

def download_task(tid, url, save_dir, browser, quality, filetype):
    tasks[tid] = {
        'status': 'downloading', 'log': [],
        'speed': '', 'eta': '', 'percent': '0%',
        'current_file': '', 'item': 0, 'total': 0, 'progress': 0
    }
    os.makedirs(save_dir, exist_ok=True)
    is_pl = 'list=' in url

    def hook(d):
        if d['status'] == 'downloading':
            fname = os.path.splitext(os.path.basename(d.get('filename','')))[0]
            spd   = d.get('_speed_str','').strip()
            eta   = d.get('_eta_str','').strip()
            pct   = d.get('_percent_str','0%').strip()
            total = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str') or ''
            tasks[tid]['speed']        = spd
            tasks[tid]['eta']          = eta
            tasks[tid]['percent']      = pct
            tasks[tid]['current_file'] = fname[:58]+'…' if len(fname)>58 else fname
            try:
                tasks[tid]['progress'] = float(pct.replace('%','').strip())
            except Exception:
                pass
            log(tid, 'DL', f'{pct}  {spd}  ETA {eta}  —  {fname[:46]}')
        elif d['status'] == 'finished':
            fname = os.path.basename(d.get('filename',''))
            log(tid, 'DONE', f'Saved: {fname}')

    outtmpl = os.path.join(
        save_dir,
        '%(playlist_index)02d - %(title)s.%(ext)s' if is_pl else '%(title)s.%(ext)s'
    )
    opts = {
        'outtmpl': outtmpl, 'progress_hooks': [hook],
        'noplaylist': not is_pl, 'quiet': True
    }
    opts.update(get_format_opts(quality, filetype))
    if browser and browser != 'none':
        opts['cookiesfrombrowser'] = (browser,)
        log(tid, 'INFO', f'Loading cookies from {browser.capitalize()}')

    log(tid, 'INFO', f'Quality: {quality.upper()}  |  Format: {filetype.upper()}  |  {"Playlist" if is_pl else "Single Video"}')

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            log(tid, 'INFO', 'Fetching video metadata…')
            info = ydl.extract_info(url, download=False)
            if is_pl:
                entries = [e for e in info.get('entries', []) if e]
                tasks[tid]['total'] = len(entries)
                log(tid, 'INFO', f'Playlist: "{info.get("title","")}" — {len(entries)} videos')
            else:
                dur = info.get('duration_string') or f'{info.get("duration","?")}s'
                log(tid, 'INFO', f'Video: "{info.get("title","")}" — {dur}')
                tasks[tid]['total'] = 1
            log(tid, 'INFO', 'Download started…')
            ydl.download([url])
        tasks[tid]['status']  = 'done'
        tasks[tid]['progress'] = 100
        tasks[tid]['speed']    = ''
        log(tid, 'SUCCESS', 'All downloads complete.')
    except Exception as e:
        tasks[tid]['status'] = 'error'
        log(tid, 'ERROR', str(e))

def start(tid, url, save_dir, browser, quality, filetype):
    t = threading.Thread(target=download_task, args=(tid, url, save_dir, browser, quality, filetype))
    t.daemon = True
    t.start()
