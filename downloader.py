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
    logs = tasks[tid]['log']
    msg = _clean(str(msg))
    if logs and logs[-1]['level'] == 'DL':
        logs[-1]['msg']  = msg
        logs[-1]['time'] = ts()
    else:
        logs.append({'time': ts(), 'level': level, 'msg': msg})

def _is_format_error(msg):
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

def _is_cookie_error(msg):
    """
    Detect ALL cookie-related failures:
    - macOS sandbox blocking file access (Safari/Firefox)
    - Chrome/Chromium DB locked while browser is open
    - Generic permission denied on cookie files
    """
    indicators = [
        'operation not permitted',
        'errno 1',
        'cookies.binarycookies',   # Safari
        'cookies.sqlite',          # Firefox
        'permission denied',
        'database is locked',      # Chrome open → SQLite lock
        'unable to open database', # Chrome cookie DB access fail
        'could not find',
        'no such file',
        'cookiesfrombrowser',
        'keyring',                 # Chrome/Chromium keyring errors on Linux
    ]
    m = msg.lower()
    return any(i in m for i in indicators)

def _cookie_error_hint(browser):
    """Return a human-readable fix message for a cookie error."""
    b = (browser or '').lower()
    if b in ('chrome', 'chromium', 'brave', 'edge'):
        return (
            f'\u274c {browser.capitalize()} cookies are locked — '
            f'{browser.capitalize()} is open and holding its cookie database. '
            f'Fix: close {browser.capitalize()} completely, then retry. '
            f'Or select \'None\' for Cookies (not needed for public videos).'
        )
    elif b == 'safari':
        return (
            '❌ Cannot read Safari cookies (macOS sandbox). '
            'Fix: go to System Settings → Privacy & Security → Full Disk Access '
            '→ add YT Downloader. Or select \'None\' for Cookies.'
        )
    elif b == 'firefox':
        return (
            '❌ Cannot read Firefox cookies (file locked or permission denied). '
            'Close Firefox completely and retry. '
            'Or select \'None\' for Cookies (not needed for public videos).'
        )
    return (
        '❌ Cookie access failed. Close the browser completely and retry, '
        'or select \'None\' for Cookies.'
    )

# Player clients tried in order — ios/android bypass most YouTube restrictions
# web = highest quality (1080p/4K). ios/android = 144p/360p only!
PLAYER_CLIENTS_LADDER = [
    ['web'],
    ['web', 'tv_embedded'],
    ['tv_embedded'],
    ['mweb'],
    ['ios'],
    ['android'],
]

def _make_base_opts(outtmpl, hook, is_pl, browser, player_clients):
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

    log(tid, 'INFO',
        f'Quality: {quality.upper()}  |  Format: {filetype.upper()}  |  '
        f'{"Playlist" if is_pl else "Single Video"}')
    if browser and browser != 'none':
        log(tid, 'INFO', f'Using cookies from {browser.capitalize()}')

    effective_browser = browser

    # ─── METADATA FETCH ─────────────────────────────────────────────────────────
    info = None
    cookie_error_shown = False

    for clients in PLAYER_CLIENTS_LADDER:
        if tasks[tid].get('cancel'):
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
            return

        base_opts = _make_base_opts(outtmpl, hook, is_pl, effective_browser, clients)

        try:
            with yt_dlp.YoutubeDL({**base_opts, 'format': 'bestvideo+bestaudio/best'}) as ydl:
                log(tid, 'INFO', 'Fetching video metadata\u2026')
                info = ydl.extract_info(url, download=False)
            break

        except Exception as e:
            msg = str(e)

            if 'cancelled' in msg.lower():
                tasks[tid]['status'] = 'cancelled'
                log(tid, 'ERROR', 'Download cancelled.')
                return

            # ── Cookie error — check FIRST, before format errors ───────────
            if _is_cookie_error(msg) and effective_browser and effective_browser != 'none':
                if not cookie_error_shown:
                    log(tid, 'WARN', _cookie_error_hint(effective_browser))
                    log(tid, 'WARN',
                        f'Retrying WITHOUT {effective_browser.capitalize()} cookies '
                        f'(public videos will still download fine)\u2026')
                    cookie_error_shown = True
                effective_browser = None  # drop cookies for all future attempts
                base_opts = _make_base_opts(outtmpl, hook, is_pl, None, clients)
                try:
                    with yt_dlp.YoutubeDL(
                        {**base_opts, 'format': 'bestvideo+bestaudio/best'}
                    ) as ydl:
                        info = ydl.extract_info(url, download=False)
                    break
                except Exception as e2:
                    msg = str(e2)
                    if _is_format_error(msg):
                        continue  # try next client set
                    tasks[tid]['status'] = 'error'
                    log(tid, 'ERROR', f'Metadata fetch failed: {msg}')
                    return

            # ── Format/client error — try next client set ───────────────
            elif _is_format_error(msg):
                continue

            # ── Hard unknown error — abort immediately ────────────────
            else:
                tasks[tid]['status'] = 'error'
                log(tid, 'ERROR', f'Metadata fetch failed: {msg}')
                return

    if info is None:
        tasks[tid]['status'] = 'error'
        log(tid, 'ERROR',
            'Could not fetch video metadata. '
            'Check your internet connection or try a different URL.')
        return

    if is_pl:
        entries = [e for e in info.get('entries', []) if e]
        tasks[tid]['total'] = len(entries)
        log(tid, 'INFO',
            f'Playlist: "{info.get("title", "")}" \u2014 {len(entries)} videos')
    else:
        dur = info.get('duration_string') or f'{info.get("duration", "?")}s'
        log(tid, 'INFO', f'Video: "{info.get("title", "")}" \u2014 {dur}')
        tasks[tid]['total'] = 1
        tasks[tid]['item']  = 0

    # ─── DOWNLOAD WITH FORMAT FALLBACK LADDER ────────────────────────────────
    best_clients = PLAYER_CLIENTS_LADDER[0]
    base_opts = _make_base_opts(outtmpl, hook, is_pl, effective_browser, best_clients)

    if effective_browser != browser and browser and browser != 'none':
        log(tid, 'WARN',
            f'Downloading without {browser.capitalize()} cookies. '
            f'Public videos work fine. For age-restricted content: '
            f'System Settings \u2192 Privacy & Security \u2192 Full Disk Access \u2192 add YT Downloader.')

    ladder = get_format_ladder(quality, filetype)
    last_error = None

    for attempt, fmt_opts in enumerate(ladder, start=1):
        if tasks[tid].get('cancel'):
            tasks[tid]['status'] = 'cancelled'
            log(tid, 'ERROR', 'Download cancelled.')
            return

        fmt_label = fmt_opts.get('format', 'best')
        if attempt > 1:
            log(tid, 'INFO',
                f'Trying fallback format [{attempt}/{len(ladder)}]: {fmt_label}')
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

            # Cookie error mid-download — strip and retry same format once
            if _is_cookie_error(msg) and effective_browser:
                log(tid, 'WARN',
                    _cookie_error_hint(effective_browser) +
                    ' Retrying without cookies\u2026')
                effective_browser = None
                base_opts = _make_base_opts(
                    outtmpl, hook, is_pl, None, best_clients)
                opts = {**base_opts, **fmt_opts}
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
