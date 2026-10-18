<div align="center">

# ⚡ VideoCompress Pro
### High-Performance Hardware-Accelerated Video Optimizer & Compressor
**Shrink massive 4K & 1080p screen recordings by 80% to 93% with zero visible quality loss.**  
*Powered by FFmpeg, GPU Hardware Acceleration (Intel QSV / NVIDIA NVENC / AMD AMF), and FastAPI.*

[![Release](https://img.shields.io/badge/Release-v1.0.0_Stable-10b981?style=for-the-badge&logo=github)](https://github.com/abidalidevv/video-compressor-pro/releases/latest)
[![Windows](https://img.shields.io/badge/Platform-Windows_x64-0078d4?style=for-the-badge&logo=windows)](https://github.com/abidalidevv/video-compressor-pro/releases/latest)
[![Web SaaS](https://img.shields.io/badge/Web_App-FastAPI_%2B_Vanilla_JS-f59e0b?style=for-the-badge&logo=fastapi)](https://github.com/abidalidevv/video-compressor-pro)
[![SSIM Score](https://img.shields.io/badge/SSIM_Fidelity-0.9925_(99.25%25)-8b5cf6?style=for-the-badge)](https://github.com/abidalidevv/video-compressor-pro)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)

<br/>

[📥 **Download VideoCompressPro.exe (Standalone Windows App)**](https://github.com/abidalidevv/video-compressor-pro/releases/latest) • [🌐 **Explore Web SaaS Mode**](#-option-2-online-web-app-saas) • [📊 **View Benchmarks**](#-real-world-benchmark--ssim-quality-test) • [🛠️ **Production Architecture**](#-production-grade-safeguards--edge-cases-solved)

</div>

---

## 📌 Why VideoCompress Pro?

Screen recorders like **OBS Studio, Loom, Zoom, Bandicam, and Windows Game Bar** produce massive MP4/MKV files (often **500 MB to 2 GB for a 15-minute recording**). Sharing them over WhatsApp, Discord, Slack, or Email is painful.

Most traditional video converters either:
1. **Destroy Text Clarity:** High compression blurs code editors, small fonts, and UI buttons.
2. **Are Painfully Slow:** CPU-only encoding takes 20–40 minutes on an average PC.
3. **Crash on Edge Cases:** Fail on odd resolutions (e.g. `1919x1081`), silent recordings, or phone variable frame rates (VFR).

**VideoCompress Pro** solves this with a tuned **two-pass constant rate factor (CRF)** pipeline combined with **GPU Hardware Acceleration**. It drops file sizes by **~93%** while mathematically retaining **99.25% visual similarity (SSIM 0.9925)**.

---

## 📊 Real-World Benchmark & SSIM Quality Test

Tested on an actual 16-minute 1080p screen recording of software development & code editing:

| Metric | Original Recording | VideoCompress Pro (Ultra Preset) | Impact |
|:---|:---:|:---:|:---:|
| **File Size** | **974.05 MB** | **71.46 MB** | **🔥 92.7% Smaller (-902.6 MB)** |
| **Resolution** | 1920 × 1080 @ 30fps | 1920 × 1080 @ 30fps | **No resolution downscaling** |
| **Duration** | 15 min 54 sec | 15 min 54 sec | **Full length preserved** |
| **Encoding Speed** | — | **~4.1 minutes** | **⚡ Powered by Intel QuickSync GPU** |
| **SSIM Visual Fidelity** | 1.0000 (Reference) | **0.9925** | **99.25% Identical to Human Eye** |
| **Code & Text Readability** | Crystal Clear | Crystal Clear | **Zero blur on 11px font** |

---

## 🚀 Two Powerful Modes Included

```text
standalone-video-compressor/
├── desktop/                      <- OPTION 1: Standalone Windows Native Application
│   ├── VideoCompressPro.exe      <- Double-click & run (No Python/setup required)
│   ├── ffmpeg.exe                <- Hardware-accelerated encoder engine
│   ├── ffprobe.exe               <- Video stream analyzer engine
│   └── video_compressor_gui.py   <- Tkinter source code
│
└── web/                          <- OPTION 2: Online Web SaaS Platform
    ├── index.html                <- Dark Executive Glassmorphic UI (Drag-and-Drop)
    ├── server.py                 <- FastAPI Async Task Queue + Auto-Clean Janitor
    └── storage/                  <- Auto-cleaned working directory
```

---

## 💻 Option 1: Desktop Native App (`VideoCompressPro.exe`)

A portable, standalone Windows desktop application with zero external dependencies.

### Key Features:
- **Zero Installation:** Extract and double-click `VideoCompressPro.exe`.
- **Dynamic GPU Auto-Detection:** Automatically detects and unlocks:
  - 🟢 **NVIDIA NVENC** (`h264_nvenc`)
  - 🔵 **Intel QuickSync** (`h264_qsv`)
  - 🔴 **AMD AMF** (`h264_amf`)
  - ⚪ **Universal Multi-core CPU** (`libx264`)
- **Interactive GUI:** Live progress bar, percentage counter, elapsed encoding timer, and instantaneous post-compression stats.
- **Cancel Anytime:** Clean abort mechanism kills background processes and deletes uncompleted temp files.
- **1-Click Open & Play:** Open the destination folder or play the compressed video instantly with system default player.

### Quick Start (Desktop):
1. [Download the latest release zip](https://github.com/abidalidevv/video-compressor-pro/releases/latest).
2. Extract the folder and double-click **`VideoCompressPro.exe`**.
3. Select your video, pick a preset (**Ultra -85% to -93%**, **Balanced -70%**, or **High Quality -40%**), and click **START COMPRESSION**.

---

## 🌐 Option 2: Online Web App (SaaS-Ready Platform)

A full-stack, enterprise-grade video compression service ready for public SaaS hosting or internal team use.

### Architecture Highlights:
- **Asynchronous Task Architecture:** Uploading a video creates an isolated UUID task (`/api/upload`) and returns immediately. The browser polls `/api/status/{task_id}` for real-time frame progress and downloads via `/api/download/{task_id}`.
- **Zero 504 Gateway Timeouts:** Traditional single-shot HTTP connections fail on Nginx (60s timeout) and Cloudflare (100s timeout). With polling, no HTTP connection ever stays open for more than 1 second.
- **Concurrency Throttling (`asyncio.Semaphore(2)`):** Limits concurrent FFmpeg processes to 2 simultaneous jobs to prevent 100% CPU lockups and server memory crashes (OOM). Excess jobs wait smoothly in an active queue.
- **Automated Janitor Loop:** Background garbage collector runs every 10 minutes and wipes uploaded videos and temp files older than 45 minutes, guaranteeing server disk space never runs out.

### Running Locally / On a VPS:
```bash
# Clone the repository
git clone https://github.com/abidalidevv/video-compressor-pro.git
cd VideoCompressPro/web

# Install dependencies
pip install fastapi uvicorn python-multipart

# Start the high-performance server
python server.py
# Server runs at http://127.0.0.1:8000
```

### Production Nginx Reverse Proxy (2 GB Upload Support):
```nginx
server {
    server_name compress.yourdomain.com;

    # Allow massive video uploads up to 2GB (Default Nginx is only 1MB!)
    client_max_body_size 2048M;
    client_body_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

> **Cloudflare Notice:** Free Cloudflare plans cap uploads at 100 MB per request. Set your upload subdomain to **DNS-Only (Grey Cloud)** in the Cloudflare dashboard to bypass the 100MB restriction.

---

## 🛡️ Production-Grade Safeguards & Edge Cases Solved

Most naive FFmpeg scripts break in real-world scenarios. VideoCompress Pro has battle-tested safeguards built into both Desktop and Web engines:

| Edge Case / Crash Scenario | How VideoCompress Pro Solves It |
|---|---|
| **Odd Dimensions Crash**<br/>*(e.g., Cropped 1919×1081 screen)* | H.264 requires dimensions divisible by 2. Auto-enforces `scale=trunc(iw/2)*2:trunc(ih/2)*2` padding so H.264 never crashes. |
| **Silent Recordings (No Audio Track)** | Passing `-c:a aac` on a video without an audio track causes FFmpeg to exit with an error. Stream analyzer inspects streams beforehand and automatically applies `-an` (no audio). |
| **VFR (Variable Frame Rate) Audio Drift** | Mobile and OBS screen recordings use VFR, which desyncs audio after a few minutes. Forced `-vsync 2` ensures constant timecode sync. |
| **GPU Driver Failure / Hardware Busy** | If hardware acceleration fails midway, the engine automatically catches the exit code and re-runs seamlessly with universal multi-core CPU `libx264`. |
| **Security & Directory Traversal** | Filenames are sanitized with strict regex `[^a-zA-Z0-9_\-\.]`, preventing path traversal attacks (`../../`). |

---

## ⚙️ Compression Presets Reference

| Preset | Target CRF | Scale Filter | Typical Savings | Best For |
|---|:---:|:---:|:---:|---|
| **⚡ Ultra Compress** | `CRF 28` | Keep 1080p / Auto-Even | **85% – 93%** | WhatsApp, Discord, Slack, Email, Helpdesk Tickets |
| **🎯 Balanced** | `CRF 24` | Force 1080p | **65% – 75%** | Web publishing, LMS courses, portfolio videos |
| **💎 High Quality** | `CRF 20` | Native | **35% – 50%** | YouTube archival, marketing assets, master backups |

---

## 🛠️ Building from Source

To compile the standalone Windows executable yourself:

```bash
cd desktop
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --clean --name "VideoCompressPro" video_compressor_gui.py
```
The compiled single-file binary will appear in `desktop/dist/VideoCompressPro.exe`.

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">
  <sub>Built with ❤️ for creators, developers, and educators tired of uploading gigabytes of screen recordings.</sub>
</div>
