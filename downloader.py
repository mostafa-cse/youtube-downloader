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
        'unable to download webpage',
        'format not available',
        'no media links found',
        'nslocalizeddescription',
    ]
    m = msg.lower()
    return any(i in m for i in indicators)

def _is_cookie_permission_error(msg):
    """Return True if macOS sandbox blocked access to the browser cookie file."""
    indicators = [
        'operation not permitted',
        'errno 1',
        'cookies.binarycookies',
        'permission denied',
        'cookies.sqlite',
        'lock',
    ]
    m = msg.lower()
    return any(i in m for i in indicators)

# Player clients to try in order — ios/android bypass many format restrictions
PLAYER_CLIENTS_LADDER = [
    ['ios', 'android', 'mweb', 'web'],
    ['android', 'web'],
    ['mweb', 'web'],
    ['web'],
]

def _make_base_opts(outtmpl, hook, is_pl, browser, player_clients, tid):
    """Build base ydl options for a given player_clients list."""
    opts = {
        'outtmpl':        outtmpl,
        'progress_hooks': [hook],
        'noplaylist':     not is_pl,
        'quiet':          True,
        'no_warnings':    False,
        'extractor_args': {'youtube': {'player_client': player_clients}},
    }
    if browser and browser != 'none':
        opts['cookiesfrombrowser'] = (browser,)
    return opts

def download_task(tid, url, save_dir, browser, quality, filetype):
    tasks[tid].update({
        'status': 'downloading', 'log': tasks[tid].get('log', []),
        'speed': '', 'eta': '', 'percent': '0%',
        'current_file': '', 'item': 0, 'total': 0, 'progress': 0,
        'cancel': False
    })
    os.makedirs(save_dir, exist_ok=True)
    is_pl = 'list=' in url

    import os as _os
    _os.environ['PATH'] = '/opt/homebrew/bin:' + _os.environ.get('PATH', '')

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

    log(tid, 'INFO', f'Quality: {quality.upper()}  |  Format: {filetype.upper()}  |  {"Playlist" if is_pl else "Single Video"}')
    if browser and browser != 'none':
        log(tid, 'INFO', f'Loading cookies from {browser.capitalize()}')

    # ── Resolve effective browser setting (handle sandbox permission errors) ──
    effective_browser = browser

    # ── Fetch metadata — try player_client ladder ────────────────────────────
    info = None
    for clients in PLAYER_CLIENTS_LADDER:
        if tasks[tid].get('cancel'):
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
            return

        base_opts = _make_base_opts(outtmpl, hook, is_pl, effective_browser, clients, tid)

        try:
            with yt_dlp.YoutubeDL({**base_opts, 'format': 'bestvideo+bestaudio/best'}) as ydl:
                log(tid, 'INFO', f'Fetching video metadata\u2026 (clients: {clients})')
                info = ydl.extract_info(url, download=False)
            break  # metadata succeeded

        except Exception as e:
            msg = str(e)

            if 'cancelled' in msg.lower():
                tasks[tid]['status'] = 'cancelled'
                log(tid, 'ERROR', 'Download cancelled.')
                return

            # ── Cookie permission denied (macOS sandbox) ──────────────────
            if _is_cookie_permission_error(msg) and effective_browser and effective_browser != 'none':
                log(tid, 'WARN',
                    f'\u26a0\ufe0f Cannot read {effective_browser.capitalize()} cookies '
                    f'(macOS sandbox restriction). Retrying without cookies\u2026')
                effective_browser = None  # drop cookies and retry
                # Rebuild base_opts without browser
                base_opts = _make_base_opts(outtmpl, hook, is_pl, None, clients, tid)
                try:
                    with yt_dlp.YoutubeDL({**base_opts, 'format': 'bestvideo+bestaudio/best'}) as ydl:
                        info = ydl.extract_info(url, download=False)
                    break
                except Exception as e2:
                    msg = str(e2)
                    # fall through to next player_clients in ladder

            # Format error — try next client set
            if _is_format_error(msg):
                log(tid, 'WARN', f'Client {clients} failed, trying next\u2026')
                continue

            # Hard error — abort
            tasks[tid]['status'] = 'error'
            log(tid, 'ERROR', f'Metadata fetch failed: {msg}')
            return

    if info is None:
        tasks[tid]['status'] = 'error'
        log(tid, 'ERROR', 'Could not fetch video metadata after all retries. '
            'Try a different quality or check your internet connection.')
        return

    if is_pl:
        entries = [e for e in info.get('entries', []) if e]
        tasks[tid]['total'] = len(entries)
        log(tid, 'INFO', f'Playlist: "{info.get("title", "")}" \u2014 {len(entries)} videos')
    else:
        dur = info.get('duration_string') or f'{info.get("duration", "?")}s'
        log(tid, 'INFO', f'Video: "{info.get("title", "")}" \u2014 {dur}')
        tasks[tid]['total'] = 1
        tasks[tid]['item']  = 0

    # ── Download with format fallback ladder ─────────────────────────────────
    # Use effective_browser (may have been set to None after cookie error)
    best_clients = PLAYER_CLIENTS_LADDER[0]
    base_opts = _make_base_opts(outtmpl, hook, is_pl, effective_browser, best_clients, tid)

    if effective_browser != browser and browser and browser != 'none':
        log(tid, 'WARN',
            f'Downloading WITHOUT {browser.capitalize()} cookies due to macOS sandbox. '
            f'Public videos will still work. For age-restricted videos, '
            f'grant Full Disk Access to YT Downloader in System Settings \u2192 Privacy.')

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
        tasks[tid]['item'] = 0

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

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

            # Cookie permission error mid-download — strip cookies and retry same format
            if _is_cookie_permission_error(msg) and effective_browser:
                effective_browser = None
                base_opts = _make_base_opts(outtmpl, hook, is_pl, None, best_clients, tid)
                opts = {**base_opts, **fmt_opts}
                log(tid, 'WARN', 'Cookie access blocked mid-download — retrying without cookies\u2026')
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    tasks[tid]['status']   = 'done'
                    tasks[tid]['progress'] = 100
                    tasks[tid]['speed']    = ''
                    log(tid, 'SUCCESS', 'All downloads complete \u2705')
                    return
                except Exception as e2:
                    last_error = str(e2)

            if _is_format_error(msg):
                log(tid, 'WARN', 'Format not available, trying next option\u2026')
                continue

            tasks[tid]['status'] = 'error'
            log(tid, 'ERROR', msg)
            return

    tasks[tid]['status'] = 'error'
    log(tid, 'ERROR',
        f'No compatible format found after {len(ladder)} attempts. '
        f'Last error: {last_error}')

def start(tid, url, save_dir, browser, quality, filetype):
    t = threading.Thread(
        target=download_task,
        args=(tid, url, save_dir, browser, quality, filetype)
    )
    t.daemon = True
    t.start()
