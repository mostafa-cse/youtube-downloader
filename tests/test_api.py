import os, tempfile, pytest
from app import app
from utils import get_format_ladder, _max_height

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b"YT Downloader" in res.data
    assert b"urlInput" in res.data

def test_static_assets(client):
    res_css = client.get('/static/style.css')
    assert res_css.status_code == 200
    res_js = client.get('/static/app.js')
    assert res_js.status_code == 200

def test_get_dir(client):
    res = client.get('/get-dir')
    assert res.status_code == 200
    data = res.get_json()
    assert 'dir' in data
    assert len(data['dir']) > 0

def test_list_files(client):
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "test_video.mp4")
        with open(sample_file, "w") as f:
            f.write("dummy video data")

        res = client.get(f'/files?folder={tmpdir}')
        assert res.status_code == 200
        files = res.get_json()
        assert "test_video.mp4" in files

def test_clear_history(client):
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "sample.mp4")
        with open(sample_file, "w") as f:
            f.write("dummy")

        res = client.post('/clear-history', json={'folder': tmpdir})
        assert res.status_code == 200
        assert res.get_json().get('success') is True

        res_after = client.get(f'/files?folder={tmpdir}')
        assert "sample.mp4" not in res_after.get_json()

def test_download_validation(client, monkeypatch):
    # Empty URL rejection
    res = client.post('/download', json={'url': ''})
    assert res.status_code == 400

    # Auto-prepend https:// to url without protocol
    import downloader
    captured = {}
    monkeypatch.setattr(downloader, 'start', lambda tid, url, *a, **k: captured.update({'url': url}))
    res2 = client.post('/download', json={'url': 'youtube.com/watch?v=dQw4w9WgXcQ'})
    assert res2.status_code == 200
    assert captured.get('url') == 'https://youtube.com/watch?v=dQw4w9WgXcQ'

def test_format_ladder_logic():
    assert _max_height('1080') == 1080
    assert _max_height('4k') == 2160
    assert _max_height('720') == 720
    assert _max_height('best') is None

    ladder_mp4 = get_format_ladder('1080', 'mp4')
    assert len(ladder_mp4) > 0
    assert ladder_mp4[0]['merge_output_format'] == 'mp4'
    assert 'acodec^=mp4a' in ladder_mp4[0]['format']

    ladder_mp3 = get_format_ladder('best', 'mp3')
    assert len(ladder_mp3) > 0
    assert ladder_mp3[0]['postprocessors'][0]['preferredcodec'] == 'mp3'

    ladder_m4a = get_format_ladder('best', 'm4a')
    assert len(ladder_m4a) > 0
    assert ladder_m4a[0]['postprocessors'][0]['preferredcodec'] == 'm4a'
    assert any(p.get('key') == 'FFmpegMetadata' for p in ladder_m4a[0]['postprocessors'])

def test_log_resolution_preview():
    import downloader
    tid = "test-preview-tid"
    downloader.tasks[tid] = {'log': []}

    # Test with video metadata
    info_video = {
        'formats': [
            {'height': 2160, 'vcodec': 'avc1'},
            {'height': 1080, 'vcodec': 'avc1'},
            {'height': 720, 'vcodec': 'avc1'},
            {'height': None, 'vcodec': 'none'}  # audio only
        ]
    }
    # Test with quality exceeding max
    downloader.tasks[tid]['log'] = []
    info_sd = {'formats': [{'height': 480, 'vcodec': 'avc1'}]}
    downloader._log_resolution_preview(tid, info_sd, '1080', 'mp4')
    messages_cap = [entry['msg'] for entry in downloader.tasks[tid]['log']]
    assert any('Requested 1080p exceeds video maximum (480p)' in m for m in messages_cap)

    # Test with audio metadata
    downloader.tasks[tid]['log'] = []
    downloader._log_resolution_preview(tid, info_video, 'best', 'mp3')
    messages_audio = [entry['msg'] for entry in downloader.tasks[tid]['log']]
    assert any('Audio extraction' in m for m in messages_audio)

def test_get_suggested_quality_logic():
    from utils import get_suggested_quality
    info_hd = {'formats': [{'height': 1080, 'vcodec': 'avc1'}, {'height': 720, 'vcodec': 'avc1'}]}
    assert get_suggested_quality(info_hd) == '1080'

    info_4k = {'formats': [{'height': 2160, 'vcodec': 'vp9'}, {'height': 720, 'vcodec': 'avc1'}]}
    assert get_suggested_quality(info_4k) == '1080'

    info_sd = {'formats': [{'height': 480, 'vcodec': 'avc1'}, {'height': 360, 'vcodec': 'avc1'}]}
    assert get_suggested_quality(info_sd) == '480'

def test_status_endpoint(client):
    import downloader
    # Non-existent task
    res = client.get('/status/non-existent-task-id')
    assert res.status_code == 200
    assert res.get_json().get('status') == 'not_found'

    # Existing task
    test_id = 'test-status-id'
    downloader.tasks[test_id] = {'status': 'downloading', 'progress': 50, 'log': []}
    res2 = client.get(f'/status/{test_id}')
    assert res2.status_code == 200
    data = res2.get_json()
    assert data['status'] == 'downloading'
    assert data['progress'] == 50

def test_cancel_endpoint(client):
    import downloader
    # Non-existent cancel
    res = client.post('/cancel/non-existent-id')
    assert res.status_code == 404
    assert res.get_json().get('success') is False

    # Existing task cancel
    test_id = 'test-cancel-id'
    downloader.tasks[test_id] = {'status': 'downloading', 'cancel': False}
    res2 = client.post(f'/cancel/{test_id}')
    assert res2.status_code == 200
    assert res2.get_json().get('success') is True
    assert downloader.tasks[test_id]['cancel'] is True

def test_cleanup_partial_files():
    import downloader
    with tempfile.TemporaryDirectory() as tmpdir:
        part_file = os.path.join(tmpdir, "video.mp4.part")
        with open(part_file, "w") as f:
            f.write("partial")
        downloader._cleanup_partial_files(tmpdir)
        assert not os.path.exists(part_file)

def test_cookie_error_detection():
    import downloader
    assert downloader._is_cookie_error("The process cannot access the file because it is being used by another process")
    assert downloader._is_cookie_error("database is locked")
    assert downloader._is_cookie_error("could not extract cookies")
    assert not downloader._is_cookie_error("HTTP 404 Not Found")

def test_pick_folder_graceful(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr('app.native_pick_folder', lambda: tmpdir)
        res = client.post('/pick-folder')
        assert res.status_code == 200
        data = res.get_json()
        assert data.get('success') is True
        assert data.get('folder') == tmpdir

def test_open_file_edge_cases(client):
    # Non-existent file
    res = client.get('/open-file?path=/path/to/non_existent_file.mp4')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is False
    assert data.get('error') == 'File not found'

    # Empty path
    res_empty = client.get('/open-file?path=')
    assert res_empty.status_code == 200
    assert res_empty.get_json().get('success') is False

def test_open_file_cross_platform(client, monkeypatch):
    import platform, subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        sample = os.path.join(tmpdir, "demo.mp4")
        with open(sample, "w") as f:
            f.write("data")

        # Test Darwin (macOS)
        called = []
        monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
        monkeypatch.setattr(subprocess, 'Popen', lambda cmd: called.append(cmd))
        res_mac = client.get(f'/open-file?path={sample}')
        assert res_mac.get_json().get('success') is True
        assert called and called[-1][0] == 'open'

        # Test Linux
        called.clear()
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')
        res_lin = client.get(f'/open-file?path={sample}')
        assert res_lin.get_json().get('success') is True
        assert called and called[-1][0] == 'xdg-open'

        # Test Windows
        win_called = []
        monkeypatch.setattr(platform, 'system', lambda: 'Windows')
        monkeypatch.setattr(os, 'startfile', lambda p: win_called.append(p), raising=False)
        res_win = client.get(f'/open-file?path={sample}')
        assert res_win.get_json().get('success') is True
        assert win_called and win_called[-1] == os.path.normpath(sample)

def test_get_file_security(client):
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "valid.mp4")
        with open(video_path, "w") as f:
            f.write("dummy video")
        
        # Valid video file
        res = client.get(f'/get-file?path={video_path}')
        assert res.status_code == 200

        # Audio formats: m4a, aac, mp3
        for ext in ('.m4a', '.aac', '.mp3'):
            audio_p = os.path.join(tmpdir, f"audio{ext}")
            with open(audio_p, "w") as af:
                af.write("audio")
            res_aud = client.get(f'/get-file?path={audio_p}')
            assert res_aud.status_code == 200

        # Non-media file (security block)
        sensitive_path = os.path.join(tmpdir, "secret.txt")
        with open(sensitive_path, "w") as f:
            f.write("secret data")
        res_sec = client.get(f'/get-file?path={sensitive_path}')
        assert res_sec.status_code == 404

def test_8k_resolution_cap():
    assert _max_height('8k') == 4320
    assert _max_height('4320') == 4320

def test_utils_pick_folder(monkeypatch):
    import utils
    monkeypatch.setattr('utils.pick_folder_linux', lambda: '/mock/folder')
    monkeypatch.setattr('utils.pick_folder_mac', lambda: '/mock/folder')
    monkeypatch.setattr('utils.pick_folder_windows', lambda: '/mock/folder')
    res = utils.pick_folder()
    assert res == '/mock/folder'

def test_system_info_endpoint(client):
    res = client.get('/get-system-info')
    assert res.status_code == 200
    data = res.get_json()
    assert 'system' in data
    assert 'default_browser' in data
    assert 'dir' in data

    res_dir = client.get('/get-dir')
    assert res_dir.status_code == 200
    assert 'system' in res_dir.get_json()

def test_download_browser_defaults(client, monkeypatch):
    import downloader
    captured = {}
    def mock_start(tid, url, save_dir, browser, quality, filetype):
        captured['browser'] = browser

    monkeypatch.setattr(downloader, 'start', mock_start)
    
    # When no browser is sent, should pick default
    res = client.post('/download', json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'})
    assert res.status_code == 200
    assert captured.get('browser') in ('safari', 'chrome')

def test_wait_for_flask_logic(monkeypatch):
    import main
    # Test unreachable endpoint timeout
    assert main.wait_for_flask(url='http://127.0.0.1:59999/unreachable', timeout=0.1) is False

    # Test reachable endpoint
    class MockResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass

    import urllib.request
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *a, **k: MockResp())
    assert main.wait_for_flask(url='http://127.0.0.1:5001/', timeout=0.5) is True

def test_main_server_mode(monkeypatch):
    import main
    called = []
    monkeypatch.setattr(main.app, 'run', lambda *a, **k: called.append(k))
    monkeypatch.setattr(main.sys, 'argv', ['main.py', '--server'])
    main.main()
    assert len(called) == 1
    assert called[0].get('port') == main.DEFAULT_PORT

def test_analyze_endpoint(client, monkeypatch):
    import downloader
    def mock_analyze(url):
        return {
            'success': True,
            'title': 'Mock Video Title',
            'duration': '3:30',
            'thumbnail': 'https://example.com/thumb.jpg',
            'is_playlist': False,
            'playlist_count': 1,
            'heights': [1080, 720, 480],
            'resolutions': downloader._format_resolution_options([1080, 720, 480]),
            'max_resolution': '1080p FHD'
        }
    monkeypatch.setattr(downloader, 'analyze_url', mock_analyze)
    
    # Missing URL
    res = client.post('/analyze', json={})
    assert res.status_code == 400
    
    # Valid URL
    res = client.post('/analyze', json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['title'] == 'Mock Video Title'
    assert len(data['resolutions']) >= 4  # Best + 1080 + 720 + 480

def test_format_resolution_options():
    import downloader
    opts_4k = downloader._format_resolution_options([2160, 1080, 720, 360])
    ids_4k = [o['id'] for o in opts_4k]
    assert 'best' in ids_4k
    assert '4k' in ids_4k
    assert '1080' in ids_4k
    assert '720' in ids_4k
    assert '360' in ids_4k
    assert '8k' not in ids_4k  # Not present in heights

    opts_720 = downloader._format_resolution_options([720, 480])
    ids_720 = [o['id'] for o in opts_720]
    assert 'best' in ids_720
    assert '720' in ids_720
    assert '480' in ids_720
    assert '1080' not in ids_720
    assert '4k' not in ids_720



