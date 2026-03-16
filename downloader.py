import yt_dlp, os, threading
from datetime import datetime
from utils import get_format_ladder
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
    tasks[tid]['log'].append({'time': ts(), 'level': level, 'msg': _clean(str(msg))})

def log_update_last(tid, level, msg):
    """Update the last log entry if it's a DL line, else append."""
    logs = tasks[tid]['log']
    msg = _clean(str(msg))
    if logs and logs[-1]['level'] == 'DL':
        logs[-1]['msg']  = msg
        logs[-1]['time'] = ts()
    else:
        logs.append({'time': ts(), 'level': level, 'msg': msg})

def _is_format_error(msg):
    """Return True if the error is a format-unavailability error (safe to retry)."""
    indicators = [
        'requested format is not available',
        'no video formats found',
        'unable to download webpage',  # can also be a transient format issue
        'format not available',
        'no media links found',
    ]
    m = msg.lower()
    return any(i in m for i in indicators)

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
        if tasks[tid].get('cancel'):
            raise Exception('Download cancelled by user')

        if d['status'] == 'downloading':
            fname = os.path.splitext(os.path.basename(d.get('filename', '')))[0]
            spd   = _clean(d.get('_speed_str', ''))
            eta   = _clean(d.get('_eta_str', ''))
            pct   = _clean(d.get('_percent_str', '0%'))
            item  = tasks[tid]['item']
            total = tasks[tid]['total']

            tasks[tid]['speed']        = spd
            tasks[tid]['eta']          = eta
            tasks[tid]['percent']      = pct
            tasks[tid]['current_file'] = fname[:58] + '\u2026' if len(fname) > 58 else fname

            try:
                tasks[tid]['progress'] = float(pct.replace('%', '').strip() or 0)
            except Exception:
                pass

            item_str = f'[{item}/{total}] ' if total > 1 else ''
            log_update_last(tid, 'DL', f'{item_str}{pct}  {spd}  ETA {eta}  \u2014  {fname[:40]}')

        elif d['status'] == 'finished':
            fname = os.path.basename(d.get('filename', ''))
            tasks[tid]['item'] = tasks[tid].get('item', 0) + 1
            item  = tasks[tid]['item']
            total = tasks[tid]['total']
            log(tid, 'DONE', f'[{item}/{total}] Saved: {fname}')

    outtmpl = os.path.join(
        save_dir,
        '%(playlist_index)02d - %(title)s.%(ext)s' if is_pl else '%(title)s.%(ext)s'
    )

    # Base ydl options shared across all attempts
    base_opts = {
        'outtmpl':        outtmpl,
        'progress_hooks': [hook],
        'noplaylist':     not is_pl,
        'quiet':          True,
        'no_warnings':    False,
        'extractor_args': {'youtube': {'player_client': ['mweb', 'web']}},
    }

    import os as _os
    _os.environ['PATH'] = '/opt/homebrew/bin:' + _os.environ.get('PATH', '')

    if browser and browser != 'none':
        base_opts['cookiesfrombrowser'] = (browser,)
        log(tid, 'INFO', f'Loading cookies from {browser.capitalize()}')

    log(tid, 'INFO', f'Quality: {quality.upper()}  |  Format: {filetype.upper()}  |  {"Playlist" if is_pl else "Single Video"}')

    # ── Fetch metadata first (format-independent) ────────────────────────────
    try:
        with yt_dlp.YoutubeDL({**base_opts, 'format': 'best'}) as ydl:
            log(tid, 'INFO', 'Fetching video metadata\u2026')
            info = ydl.extract_info(url, download=False)
            if is_pl:
                entries = [e for e in info.get('entries', []) if e]
                tasks[tid]['total'] = len(entries)
                log(tid, 'INFO', f'Playlist: "{info.get("title", "")}" \u2014 {len(entries)} videos')
            else:
                dur = info.get('duration_string') or f'{info.get("duration", "?")}s'
                log(tid, 'INFO', f'Video: "{info.get("title", "")}" \u2014 {dur}')
                tasks[tid]['total'] = 1
                tasks[tid]['item']  = 0
    except Exception as e:
        msg = str(e)
        if 'cancelled' in msg.lower():
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
        else:
            tasks[tid]['status'] = 'error'
            log(tid, 'ERROR', f'Metadata fetch failed: {msg}')
        return

    # ── Download with fallback ladder ────────────────────────────────────────
    ladder = get_format_ladder(quality, filetype)
    last_error = None

    for attempt, fmt_opts in enumerate(ladder, start=1):
        if tasks[tid].get('cancel'):
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
            return

        fmt_label = fmt_opts.get('format', 'best')
        if attempt > 1:
            log(tid, 'INFO', f'Trying fallback format [{attempt}/{len(ladder)}]: {fmt_label}')
        else:
            log(tid, 'INFO', 'Download started\u2026')

        opts = {**base_opts, **fmt_opts}
        # Reset item counter for each attempt so UI stays clean
        tasks[tid]['item'] = 0

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            # ── Success ──────────────────────────────────────────────────────
            tasks[tid]['status']   = 'done'
            tasks[tid]['progress'] = 100
            tasks[tid]['speed']    = ''
            log(tid, 'SUCCESS', 'All downloads complete \u2705')
            return

        except Exception as e:
            msg = str(e)
            last_error = msg

            if 'cancelled' in msg.lower():
                tasks[tid]['status'] = 'cancelled'
                log(tid, 'ERROR', 'Download cancelled.')
                return

            if _is_format_error(msg):
                # Safe to retry with next format in the ladder
                log(tid, 'WARN', f'Format not available, trying next option\u2026')
                continue

            # Non-format error — don't retry
            tasks[tid]['status'] = 'error'
            log(tid, 'ERROR', msg)
            return

    # All ladder options exhausted
    tasks[tid]['status'] = 'error'
    log(tid, 'ERROR',
        f'No compatible format found for this video after {len(ladder)} attempts. '
        f'Last error: {last_error}')

def start(tid, url, save_dir, browser, quality, filetype):
    t = threading.Thread(
        target=download_task,
        args=(tid, url, save_dir, browser, quality, filetype)
    )
    t.daemon = True
    t.start()
