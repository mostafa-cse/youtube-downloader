import yt_dlp, os, threading
from datetime import datetime
from utils import get_format_opts
import re as _re

def _clean(s):
    if not s: return s
    s = str(s)
    s = _re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', s)
    s = _re.sub(r'\[[0-9;]*[mGKHFJABCDsu]', '', s)
    s = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    return s.strip()

tasks = {}

def ts():
    return datetime.now().strftime('%H:%M:%S')

def log(tid, level, msg):
    tasks[tid]['log'].append({'time': ts(), 'level': level, 'msg': _clean(msg)})

def download_task(tid, url, save_dir, browser, quality, filetype):
    tasks[tid].update({
        'status': 'downloading', 'log': tasks[tid].get('log', []),
        'speed': '', 'eta': '', 'percent': '0%',
        'current_file': '', 'item': 0, 'total': 0, 'progress': 0,
        'cancel': False
    })
    os.makedirs(save_dir, exist_ok=True)
    is_pl = 'list=' in url

    def hook(d):
        # Check cancel flag
        if tasks[tid].get('cancel'):
            raise Exception('Download cancelled by user')

        if d['status'] == 'downloading':
            fname = os.path.splitext(os.path.basename(d.get('filename','')))[0]
            spd  = _clean(d.get('_speed_str',''))
            eta  = _clean(d.get('_eta_str',''))
            pct  = _clean(d.get('_percent_str','0%'))
            tasks[tid]['speed']        = spd
            tasks[tid]['eta']          = eta
            tasks[tid]['percent']      = pct
            tasks[tid]['current_file'] = fname[:58]+'…' if len(fname)>58 else fname
            try:
                tasks[tid]['progress'] = float(pct.replace('%','').strip() or 0)
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
        tasks[tid]['status']   = 'done'
        tasks[tid]['progress'] = 100
        tasks[tid]['speed']    = ''
        log(tid, 'SUCCESS', 'All downloads complete.')
    except Exception as e:
        msg = str(e)
        if 'cancelled' in msg.lower():
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
        else:
            tasks[tid]['status'] = 'error'
            log(tid, 'ERROR', msg)

def start(tid, url, save_dir, browser, quality, filetype):
    t = threading.Thread(target=download_task, args=(tid, url, save_dir, browser, quality, filetype))
    t.daemon = True
    t.start()
