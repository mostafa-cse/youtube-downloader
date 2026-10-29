<p align="center">
  <img src="docs/assets/logo.png" width="96" height="96" alt="YT Downloader logo" />
</p>

<h1 align="center">🎬 YT Downloader for macOS, Windows &amp; Linux</h1>
<p align="center">A professional, free &amp; open-source desktop app to download YouTube videos, playlists &amp; audio — any quality, zero ads.</p>

<p align="center">
  <a href="https://mostafa-cse.github.io/youtube-downloader/"><img src="https://img.shields.io/badge/🌐%20Website-Visit%20Now-3b82f6?style=for-the-badge" alt="Website"/></a>
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/mostafa-cse/youtube-downloader?style=for-the-badge&label=Download&color=10b981" alt="Latest Release"/></a>
  <img src="https://img.shields.io/github/downloads/mostafa-cse/youtube-downloader/total?style=for-the-badge&color=8b5cf6&label=Downloads" alt="Downloads"/>
  <img src="https://img.shields.io/badge/Platforms-macOS%20|%20Windows%20|%20Linux-black?style=for-the-badge" alt="Platforms"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
</p>

---

## 🌐 Website

**[https://mostafa-cse.github.io/youtube-downloader/](https://mostafa-cse.github.io/youtube-downloader/)**

Full documentation, screenshots, FAQ, and one-click download — all on the landing page.

---

## ✨ Features

- 🎥 Download single videos, full playlists, or entire channels
- 🔊 Audio extraction — MP3 / M4A (320kbps)
- 📺 Quality selector — Best / 8K / 4K / 1080p / 720p / 480p / 360p
- 📦 Format selector — MP4 / MKV / MP3 / M4A
- ⚡ Live download speed, ETA & real-time progress bar
- 🍪 Cookie support — Safari / Chrome / Firefox / Edge / Arc (age-restricted videos)
- 🎨 Modern Liquid Glass dark UI
- 📁 Custom save folder picker with persistent preference
- 🔒 100% private — zero telemetry, zero analytics
- 💻 Cross-platform: macOS (Apple Silicon M1/M2/M3/M4 & Intel), Windows 10/11, and Linux (Ubuntu, Debian, Mint)

---

## 📥 Download & Install

| OS | Package | Instructions |
|---|---|---|
| **🪟 Windows** | [`YT-Downloader.exe`](../../releases/latest) | Run `.exe` directly. No installation or setup required. |
| **🐧 Linux** | [`yt-downloader-amd64.deb`](../../releases/latest) | Install with `sudo dpkg -i yt-downloader-*.deb`. |
| **🍎 macOS** | [`YT-Downloader.dmg`](../../releases/latest) | Open DMG &rarr; drag to **Applications**. |

### macOS First Launch (Apple Silicon M1/M2/M3/M4 & Intel)
- Right-click **YT Downloader.app** &rarr; **Open** &rarr; **Open**, OR
- Go to **System Settings** &rarr; **Privacy & Security** &rarr; scroll to **Security** &rarr; click **Open Anyway**, OR
- If macOS displays *"damaged and can't be opened"*, run this one-time command in Terminal:
  ```bash
  xattr -cr "/Applications/YT Downloader.app"
  ```

> ✅ No Python, no FFmpeg, no Terminal setup needed for end users. FFmpeg is automatically bundled inside all desktop builds.

---

## 🛠 Run From Source

```bash
# Clone
git clone https://github.com/mostafa-cse/youtube-downloader.git
cd youtube-downloader

# Setup venv
python3 -m venv venv
venv/bin/pip install flask yt-dlp pywebview static-ffmpeg Pillow

# Run
venv/bin/python main.py
```

---

## 🗺 Roadmap

- [ ] App notarization (v2.0)
- [ ] Concurrent multi-download queue
- [ ] Subtitle download support
- [ ] Thumbnail embedding

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss what you'd like to change.

---

## 📄 License

[MIT License](LICENSE) — © 2026 [Mostafa Kamal](https://github.com/mostafa-cse)
