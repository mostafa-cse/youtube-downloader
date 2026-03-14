<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS-black?style=for-the-badge&logo=apple&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/yt--dlp-Latest-red?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
</p>

<h1 align="center">🎬 YT Downloader</h1>
<p align="center">A professional macOS app to download YouTube videos & playlists — any quality, any format.</p>

---

## ✨ Features

- 🎥 Download single videos or full playlists
- 🔊 Audio extraction — MP3 / M4A (320kbps)
- 📺 Quality selector — Best / 4K / 1080p / 720p / 480p / 360p
- 📦 Format selector — MP4 / MKV / MP3 / M4A
- ⚡ Live download speed, ETA & progress bar
- 📂 Auto file counter — tracks downloaded files in real time
- 🍪 Cookie support — Safari / Chrome / Firefox (for age-restricted videos)
- 🎨 Liquid Glass dark UI — built for macOS
- 📁 Custom save folder picker

---

## 📥 Download & Install (macOS)

1. Download **`YT-Downloader-by-M0stafa.dmg`** from [Releases](../../releases)
2. Double-click the `.dmg` file
3. Drag **YT Downloader** → **Applications**
4. Right-click the app → **Open** → **Open** (first launch only, bypasses Gatekeeper)

> ✅ No Python, no Terminal, no setup needed. ffmpeg is bundled inside.

---

## 🛠 Run From Source

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/youtube-downloader.git
cd youtube-downloader

# Setup venv
python3 -m venv venv
venv/bin/pip install flask yt-dlp pywebview static-ffmpeg Pillow

# Run
venv/bin/python main.py


***

## Step 5: Create `.gitignore`

```bash
cat > ~/youtube-downloader/.gitignore << 'EOF'
venv/
__pycache__/
*.pyc
*.pyo
build/
dist/
*.spec
*.dmg
*.egg-info/
.DS_Store
downloads/
*.zip
