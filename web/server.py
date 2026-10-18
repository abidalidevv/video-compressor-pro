import os
import re
import time
import shutil
import asyncio
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VideoCompress Pro High-Performance Server")

# Allow CORS for cross-domain API usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

# Binary discovery
def get_binary_paths():
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe

    common_dirs = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages/Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-essentials_build/bin",
        Path(__file__).resolve().parent.parent / "desktop",
        Path("C:/ffmpeg/bin"),
        Path("/usr/bin"),
        Path("/usr/local/bin")
    ]
    for d in common_dirs:
        f = d / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        p = d / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if f.exists():
            return str(f), str(p) if p.exists() else "ffprobe"

    return "ffmpeg", "ffprobe"

FFMPEG_BIN, FFPROBE_BIN = get_binary_paths()

# Concurrency throttling: Max 2 FFmpeg encoding jobs running in parallel to prevent 100% CPU lockup
MAX_CONCURRENT_ENCODES = 2
ENCODE_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_ENCODES)

# In-Memory Task Registry
TASKS: Dict[str, Dict[str, Any]] = {}

def check_has_audio(file_path: str) -> bool:
    try:
        cmd = [
            FFPROBE_BIN, "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        return "audio" in res.stdout
    except Exception:
        return True

def get_video_duration(file_path: str) -> float:
    try:
        cmd = [
            FFPROBE_BIN, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        return float(res.stdout.strip())
    except Exception:
        return 0.0

async def janitor_cleanup_task():
    """Background loop that deletes temp files and expired tasks older than 45 minutes"""
    while True:
        try:
            now = time.time()
            expired_tasks = []
            for tid, tinfo in list(TASKS.items()):
                # Delete files older than 45 minutes
                if now - tinfo.get("created_at", now) > 2700:
                    expired_tasks.append(tid)
                    folder = STORAGE_DIR / tid
                    if folder.exists():
                        shutil.rmtree(folder, ignore_errors=True)

            for tid in expired_tasks:
                TASKS.pop(tid, None)
        except Exception as e:
            print(f"[Janitor Error] {e}")

        await asyncio.sleep(600) # Run every 10 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(janitor_cleanup_task())

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = BASE_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_file.read_text(encoding="utf-8")

async def process_video_job(task_id: str, input_path: Path, output_path: Path, crf: int, resolution: str, orig_name: str):
    async with ENCODE_SEMAPHORE:
        TASKS[task_id]["status"] = "processing"
        TASKS[task_id]["progress"] = 5

        # 1. Probe duration & audio
        duration = await asyncio.to_thread(get_video_duration, str(input_path))
        has_audio = await asyncio.to_thread(check_has_audio, str(input_path))

        # 2. Build FFmpeg command with even dimension protections
        cmd = [FFMPEG_BIN, "-y", "-i", str(input_path)]

        # Resolution filter
        if resolution != "original" and resolution.isdigit():
            target_width = int(resolution)
            vf = f"scale={target_width}:-2"
        else:
            # Force even dimensions for any odd-pixel recording (prevents H.264 crash)
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

        cmd.extend(["-vf", vf])

        # Codec & quality
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(crf)
        ])

        # Audio stream handling
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.extend(["-an"])

        cmd.extend(["-vsync", "2", str(output_path)])

        # Run process and parse progress
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stderr=asyncio.subprocess.PIPE,
                startupinfo=startupinfo
            )

            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="ignore")
                match = time_pattern.search(line_str)
                if match and duration > 0:
                    hours, mins, secs = match.groups()
                    current_secs = int(hours) * 3600 + int(mins) * 60 + float(secs)
                    pct = min(99.0, max(5.0, (current_secs / duration) * 100))
                    TASKS[task_id]["progress"] = round(pct, 1)

            await process.wait()

            if process.returncode == 0 and output_path.exists():
                orig_sz = input_path.stat().st_size
                new_sz = output_path.stat().st_size
                savings = max(0, int((1 - new_sz / orig_sz) * 100))

                TASKS[task_id].update({
                    "status": "completed",
                    "progress": 100,
                    "orig_size": orig_sz,
                    "new_size": new_sz,
                    "savings_pct": savings,
                    "download_name": f"{Path(orig_name).stem}_compressed.mp4"
                })
            else:
                TASKS[task_id]["status"] = "failed"
                TASKS[task_id]["error"] = "FFmpeg process failed during encoding."

        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["error"] = str(e)

@app.post("/api/upload")
async def upload_for_compression(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    crf: int = Form(26),
    resolution: str = Form("original")
):
    """Asynchronous Non-Blocking Upload: Creates a task ID and returns immediately. Eliminates 504 timeouts."""
    task_id = str(uuid.uuid4())
    task_dir = STORAGE_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize input filename
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file.filename or "video.mp4")
    input_file = task_dir / safe_name
    output_file = task_dir / f"compressed_{safe_name}.mp4"

    # Stream write upload to disk
    with open(input_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "input_file": str(input_file),
        "output_file": str(output_file),
        "orig_name": file.filename,
        "created_at": time.time(),
        "orig_size": input_file.stat().st_size
    }

    background_tasks.add_task(
        process_video_job,
        task_id, input_file, output_file, crf, resolution, file.filename
    )

    return JSONResponse({
        "success": True,
        "task_id": task_id,
        "status": "queued",
        "message": "Video queued for compression."
    })

@app.get("/api/status/{task_id}")
async def check_task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "progress": task.get("progress", 0),
        "orig_size": task.get("orig_size", 0),
        "new_size": task.get("new_size", 0),
        "savings_pct": task.get("savings_pct", 0),
        "error": task.get("error")
    }

@app.get("/api/download/{task_id}")
async def download_compressed(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Compression not yet finished")

    out_path = Path(task["output_file"])
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing")

    return FileResponse(
        path=str(out_path),
        filename=task.get("download_name", "compressed_video.mp4"),
        media_type="video/mp4"
    )

# Backward-compatible direct single-shot endpoint
@app.post("/api/compress")
async def compress_video_direct(
    file: UploadFile = File(...),
    crf: int = Form(26),
    resolution: str = Form("original")
):
    task_id = str(uuid.uuid4())
    task_dir = STORAGE_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file.filename or "video.mp4")
    input_file = task_dir / safe_name
    output_file = task_dir / f"compressed_{safe_name}.mp4"

    with open(input_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "created_at": time.time()
    }

    await process_video_job(task_id, input_file, output_file, crf, resolution, file.filename)

    if TASKS[task_id].get("status") == "completed" and output_file.exists():
        return FileResponse(
            path=str(output_file),
            filename=f"{Path(file.filename).stem}_compressed.mp4",
            media_type="video/mp4"
        )
    else:
        err = TASKS[task_id].get("error", "Compression failed")
        raise HTTPException(status_code=500, detail=err)

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(" VideoCompress Pro High-Performance Server")
    print(f" Web UI:  http://127.0.0.1:8000")
    print(f" Engine:  {FFMPEG_BIN}")
    print(f" Workers: Max {MAX_CONCURRENT_ENCODES} concurrent FFmpeg instances")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
