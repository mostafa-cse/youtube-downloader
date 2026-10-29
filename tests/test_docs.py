import os

def test_docs_structure():
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
    assert os.path.isdir(docs_dir), "docs/ directory must exist"
    
    index_file = os.path.join(docs_dir, 'index.html')
    assert os.path.isfile(index_file), "docs/index.html must exist"
    
    with open(index_file, 'r', encoding='utf-8') as f:
        html = f.read()

    # Verify essential elements
    assert "<title>" in html, "Page must have a title tag"
    assert "YT Downloader" in html
    assert "Windows" in html and "Linux" in html and "macOS" in html
    assert 'id="download-mac"' in html, "Must include macOS download card"
    assert 'id="download-win"' in html, "Must include Windows download card"
    assert 'id="download-linux"' in html, "Must include Linux download card"
    assert "YT-Downloader.exe" in html, "Must mention Windows EXE"
    assert "yt-downloader-amd64.deb" in html, "Must mention Linux DEB"
    assert "YT-Downloader.dmg" in html, "Must mention macOS DMG"
    assert "schema.org" in html, "Page must include structured SEO data"
    assert "robots.txt" in os.listdir(docs_dir), "docs/robots.txt must exist"
    assert "sitemap.xml" in os.listdir(docs_dir), "docs/sitemap.xml must exist"

def test_docs_assets():
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
    assets_dir = os.path.join(docs_dir, 'assets')
    assert os.path.isdir(assets_dir), "docs/assets directory must exist"
    assert "logo.png" in os.listdir(assets_dir), "docs/assets/logo.png must exist"
