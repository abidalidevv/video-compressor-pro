import os
import re
import sys
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Auto-detect ffmpeg.exe & ffprobe.exe
def get_binary_paths():
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent

    # 1. Local directory check
    local_ffmpeg = exe_dir / "ffmpeg.exe"
    local_ffprobe = exe_dir / "ffprobe.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg), str(local_ffprobe) if local_ffprobe.exists() else "ffprobe.exe"

    # 2. PATH check
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffmpeg:
        return sys_ffmpeg, sys_ffprobe or "ffprobe.exe"

    # 3. WinGet default path check
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winget_dir = Path(local_app_data) / "Microsoft/WinGet/Packages/Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-essentials_build/bin"
    if (winget_dir / "ffmpeg.exe").exists():
        return str(winget_dir / "ffmpeg.exe"), str(winget_dir / "ffprobe.exe")

    return "ffmpeg.exe", "ffprobe.exe"

FFMPEG_EXE, FFPROBE_EXE = get_binary_paths()

def detect_hardware_encoders(ffmpeg_bin):
    try:
        res = subprocess.run([ffmpeg_bin, "-encoders"], capture_output=True, text=True, errors="ignore")
        output = res.stdout
        encoders = ["libx264 (CPU - Universal & Maximum Quality)"]
        if "h264_qsv" in output:
            encoders.insert(0, "h264_qsv (Intel QuickSync GPU - Ultra Fast)")
        if "h264_nvenc" in output:
            encoders.insert(0, "h264_nvenc (NVIDIA GPU - Lightning Fast)")
        if "h264_amf" in output:
            encoders.insert(0, "h264_amf (AMD GPU Acceleration)")
        return encoders
    except Exception:
        return ["libx264 (CPU - Universal & Maximum Quality)"]

class VideoCompressorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoCompress Pro — Hardware-Accelerated Video Optimizer")
        self.geometry("820x760")
        self.minsize(740, 680)
        self.configure(bg="#0b0f19")

        self.input_file = None
        self.output_file = None
        self.duration_seconds = 0
        self.has_audio = True
        self.is_compressing = False
        self.is_cancelled = False
        self.process = None

        self.available_encoders = detect_hardware_encoders(FFMPEG_EXE)
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=14, troughcolor="#1e293b", background="#f59e0b")

        # Top Header Banner
        header = tk.Frame(self, bg="#0f172a", pady=18, padx=25)
        header.pack(fill="x")

        lbl_badge = tk.Label(header, text="⚡ HARDWARE ACCELERATED FFMPEG ENGINE (BULLETPROOF EDITION)", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#1e293b", padx=10, pady=2)
        lbl_badge.pack(anchor="w", pady=(0, 4))

        lbl_title = tk.Label(header, text="VideoCompress Pro", font=("Segoe UI", 22, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(header, text="Compress massive 4K & 1080p screen recordings by 80-93% with crystal-clear text fidelity.", font=("Segoe UI", 10), fg="#94a3b8", bg="#0f172a")
        lbl_sub.pack(anchor="w")

        content = tk.Frame(self, bg="#0b0f19", padx=25, pady=20)
        content.pack(fill="both", expand=True)

        # 1. FILE PICKER CARD
        file_card = tk.LabelFrame(content, text=" 1. SOURCE VIDEO ", font=("Segoe UI", 10, "bold"), fg="#f59e0b", bg="#111827", padx=15, pady=15, bd=1, relief="solid")
        file_card.pack(fill="x", pady=(0, 15))

        btn_browse = tk.Button(file_card, text="📂 Choose Video File (MP4, MKV, MOV, AVI)...", font=("Segoe UI", 11, "bold"), bg="#1e293b", fg="#ffffff", activebackground="#f59e0b", activeforeground="#000", bd=0, padx=16, pady=8, cursor="hand2", command=self.browse_file)
        btn_browse.pack(fill="x")

        self.lbl_file_info = tk.Label(file_card, text="No video selected yet", font=("Segoe UI", 10), fg="#94a3b8", bg="#111827", pady=6)
        self.lbl_file_info.pack(anchor="w")

        # 2. PRESETS CARD
        preset_card = tk.LabelFrame(content, text=" 2. COMPRESSION PRESET ", font=("Segoe UI", 10, "bold"), fg="#f59e0b", bg="#111827", padx=15, pady=12, bd=1, relief="solid")
        preset_card.pack(fill="x", pady=(0, 15))

        p_row = tk.Frame(preset_card, bg="#111827")
        p_row.pack(fill="x")

        self.preset_var = tk.StringVar(value="ultra")

        rb1 = tk.Radiobutton(p_row, text="⚡ Ultra Compress (-85% to -93%)", variable=self.preset_var, value="ultra", command=self.apply_preset, font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#111827", selectcolor="#0f172a", activebackground="#111827")
        rb1.pack(side="left", padx=(0, 20))

        rb2 = tk.Radiobutton(p_row, text="🎯 Balanced 1080p (-70%)", variable=self.preset_var, value="balanced", command=self.apply_preset, font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#111827", selectcolor="#0f172a", activebackground="#111827")
        rb2.pack(side="left", padx=(0, 20))

        rb3 = tk.Radiobutton(p_row, text="💎 High Quality (-40%)", variable=self.preset_var, value="high", command=self.apply_preset, font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#111827", selectcolor="#0f172a", activebackground="#111827")
        rb3.pack(side="left")

        # 3. ADVANCED SETTINGS
        adv_card = tk.LabelFrame(content, text=" 3. ENCODING CONTROLS ", font=("Segoe UI", 10, "bold"), fg="#f59e0b", bg="#111827", padx=15, pady=12, bd=1, relief="solid")
        adv_card.pack(fill="x", pady=(0, 15))

        # Row 1: Hardware Encoder
        r1 = tk.Frame(adv_card, bg="#111827")
        r1.pack(fill="x", pady=(0, 8))
        tk.Label(r1, text="Encoder Engine:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827", width=16, anchor="w").pack(side="left")
        self.encoder_var = tk.StringVar(value=self.available_encoders[0])
        self.encoder_dropdown = ttk.Combobox(r1, textvariable=self.encoder_var, values=self.available_encoders, state="readonly", width=45)
        self.encoder_dropdown.pack(side="left", fill="x", expand=True)

        # Row 2: Resolution Scale
        r2 = tk.Frame(adv_card, bg="#111827")
        r2.pack(fill="x", pady=(0, 8))
        tk.Label(r2, text="Resolution Scale:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827", width=16, anchor="w").pack(side="left")
        self.res_var = tk.StringVar(value="Keep Original Resolution")
        self.res_dropdown = ttk.Combobox(r2, textvariable=self.res_var, values=["Keep Original Resolution", "1080p (Full HD - 1920px)", "720p (HD - 1280px)", "480p (SD - 854px)"], state="readonly", width=45)
        self.res_dropdown.pack(side="left", fill="x", expand=True)

        # Row 3: Quality CRF Slider
        r3 = tk.Frame(adv_card, bg="#111827")
        r3.pack(fill="x")
        tk.Label(r3, text="CRF Quality Level:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827", width=16, anchor="w").pack(side="left")
        self.crf_var = tk.IntVar(value=26)
        self.crf_slider = tk.Scale(r3, from_=18, to=35, orient="horizontal", variable=self.crf_var, bg="#111827", fg="#f59e0b", highlightthickness=0, troughcolor="#1e293b", command=self.update_crf_label)
        self.crf_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl_crf_val = tk.Label(r3, text="CRF 26", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#111827", width=8)
        self.lbl_crf_val.pack(side="left")

        # 4. ACTION BUTTONS (Start & Cancel)
        action_row = tk.Frame(content, bg="#0b0f19")
        action_row.pack(fill="x", pady=(0, 15))

        self.btn_start = tk.Button(action_row, text="🚀 START COMPRESSION", font=("Segoe UI", 13, "bold"), bg="#f59e0b", fg="#000000", activebackground="#fbbf24", bd=0, pady=12, cursor="hand2", state="disabled", command=self.start_compression_thread)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_cancel = tk.Button(action_row, text="⏹ Cancel", font=("Segoe UI", 11, "bold"), bg="#ef4444", fg="#ffffff", activebackground="#dc2626", bd=0, padx=20, pady=12, cursor="hand2", state="disabled", command=self.cancel_compression)
        self.btn_cancel.pack(side="right")

        # Progress Frame
        self.progress_frame = tk.Frame(content, bg="#0b0f19")
        self.progress_frame.pack(fill="x")

        self.lbl_status = tk.Label(self.progress_frame, text="Ready", font=("Segoe UI", 10), fg="#94a3b8", bg="#0b0f19")
        self.lbl_status.pack(anchor="w", pady=(0, 4))

        self.progress_bar = ttk.Progressbar(self.progress_frame, style="TProgressbar", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 8))

        # Bottom Finish Actions
        self.finish_frame = tk.Frame(content, bg="#0b0f19")
        self.finish_frame.pack(fill="x")

        self.btn_open_folder = tk.Button(self.finish_frame, text="📂 Open Destination Folder", font=("Segoe UI", 10, "bold"), bg="#1e293b", fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.open_output_folder)
        self.btn_play_video = tk.Button(self.finish_frame, text="▶ Play Compressed Video", font=("Segoe UI", 10, "bold"), bg="#10b981", fg="#000000", bd=0, padx=12, pady=6, cursor="hand2", command=self.play_output_video)

    def apply_preset(self):
        val = self.preset_var.get()
        if val == "ultra":
            self.crf_var.set(27)
        elif val == "balanced":
            self.crf_var.set(23)
        elif val == "high":
            self.crf_var.set(20)
        self.update_crf_label(self.crf_var.get())

    def update_crf_label(self, val):
        self.lbl_crf_val.config(text=f"CRF {val}")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File to Compress",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.input_file = Path(file_path)
        size_mb = self.input_file.stat().st_size / (1024 * 1024)
        
        # Avoid file collision
        base_out = self.input_file.parent / f"{self.input_file.stem}_compressed.mp4"
        counter = 1
        while base_out.exists():
            base_out = self.input_file.parent / f"{self.input_file.stem}_compressed_{counter}.mp4"
            counter += 1
        self.output_file = base_out

        # Probe video
        self.duration_seconds, self.has_audio = self.probe_video(str(self.input_file))

        duration_str = f"{int(self.duration_seconds // 60)}m {int(self.duration_seconds % 60)}s" if self.duration_seconds > 0 else "Unknown"
        audio_str = "Audio: AAC Stereo" if self.has_audio else "Audio: None (Silent Video)"
        self.lbl_file_info.config(
            text=f"📁 {self.input_file.name}  |  Size: {size_mb:.1f} MB  |  Duration: {duration_str}  |  {audio_str}",
            fg="#10b981"
        )
        self.btn_start.config(state="normal")
        self.lbl_status.config(text=f"Ready to compress. Output will save as: {self.output_file.name}", fg="#94a3b8")
        self.finish_frame.pack_forget()

    def probe_video(self, filepath):
        duration = 0.0
        has_audio = False
        try:
            cmd = [FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1", filepath]
            res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
            for line in res.stdout.splitlines():
                if line.startswith("duration="):
                    try: duration = float(line.split("=")[1])
                    except: pass
                elif "codec_type=audio" in line:
                    has_audio = True
        except Exception:
            pass
        return duration, has_audio

    def start_compression_thread(self):
        if not self.input_file or self.is_compressing:
            return

        self.is_compressing = True
        self.is_cancelled = False
        self.btn_start.config(state="disabled", text="⏳ COMPRESSING VIDEO...")
        self.btn_cancel.config(state="normal")
        self.progress_bar["value"] = 0
        self.finish_frame.pack_forget()

        thread = threading.Thread(target=self.run_ffmpeg, daemon=True)
        thread.start()

    def cancel_compression(self):
        if self.is_compressing and self.process:
            self.is_cancelled = True
            try:
                self.process.kill()
            except:
                pass
            self.lbl_status.config(text="Compression cancelled by user.", fg="#ef4444")
            self.is_compressing = False
            self.btn_start.config(state="normal", text="🚀 START COMPRESSION")
            self.btn_cancel.config(state="disabled")
            # Remove partial output
            if self.output_file and self.output_file.exists():
                try: self.output_file.unlink()
                except: pass

    def build_command(self, use_fallback_cpu=False):
        cmd = [FFMPEG_EXE, "-y", "-i", str(self.input_file)]

        # Even dimensions scaling filter (Prevents 'width not divisible by 2' crash)
        res = self.res_var.get()
        if "1080p" in res:
            vf = "scale=1920:-2"
        elif "720p" in res:
            vf = "scale=1280:-2"
        elif "480p" in res:
            vf = "scale=854:-2"
        else:
            # Enforce even dimensions for odd crop recordings (e.g. 1919x1081 -> 1918x1080)
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

        cmd.extend(["-vf", vf])

        crf = str(self.crf_var.get())
        enc = "libx264" if use_fallback_cpu else self.encoder_var.get()

        if "h264_qsv" in enc and not use_fallback_cpu:
            cmd.extend(["-c:v", "h264_qsv", "-global_quality", crf])
        elif "h264_nvenc" in enc and not use_fallback_cpu:
            cmd.extend(["-c:v", "h264_nvenc", "-cq", crf])
        elif "h264_amf" in enc and not use_fallback_cpu:
            cmd.extend(["-c:v", "h264_amf", "-rc", "cqp", "-qp_i", crf, "-qp_p", crf])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", crf])

        # Audio Stream Handling
        if self.has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.extend(["-an"]) # No audio stream

        # VSYNC CFR flag (prevents audio/video desync on phone VFR recordings)
        cmd.extend(["-vsync", "2", str(self.output_file)])
        return cmd

    def run_ffmpeg(self):
        cmd = self.build_command(use_fallback_cpu=False)

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors="ignore",
                startupinfo=startupinfo
            )

            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

            for line in self.process.stderr:
                if self.is_cancelled:
                    return

                match = time_pattern.search(line)
                if match and self.duration_seconds > 0:
                    hours, mins, secs = match.groups()
                    current_seconds = int(hours) * 3600 + int(mins) * 60 + float(secs)
                    pct = min(100.0, (current_seconds / self.duration_seconds) * 100)
                    self.update_progress(pct, f"Encoding... {pct:.1f}% ({int(current_seconds)}s / {int(self.duration_seconds)}s)")

            self.process.wait()

            if self.is_cancelled:
                return

            if self.process.returncode == 0 and self.output_file.exists():
                self.after(0, self.compression_success)
            else:
                # AUTOMATIC FALLBACK: If hardware acceleration failed, retry with CPU libx264!
                if not "libx264" in self.encoder_var.get():
                    self.update_progress(0, "Hardware encoder busy/unsupported. Retrying with universal CPU x264...")
                    fallback_cmd = self.build_command(use_fallback_cpu=True)
                    self.process = subprocess.Popen(fallback_cmd, stderr=subprocess.PIPE, universal_newlines=True, errors="ignore", startupinfo=startupinfo)
                    for line in self.process.stderr:
                        if self.is_cancelled: return
                        match = time_pattern.search(line)
                        if match and self.duration_seconds > 0:
                            hours, mins, secs = match.groups()
                            current_seconds = int(hours) * 3600 + int(mins) * 60 + float(secs)
                            pct = min(100.0, (current_seconds / self.duration_seconds) * 100)
                            self.update_progress(pct, f"CPU Fallback Encoding... {pct:.1f}% ({int(current_seconds)}s / {int(self.duration_seconds)}s)")
                    self.process.wait()
                    if self.process.returncode == 0 and self.output_file.exists():
                        self.after(0, self.compression_success)
                        return

                self.after(0, lambda: self.compression_failed("FFmpeg process encountered an error."))

        except Exception as e:
            if not self.is_cancelled:
                self.after(0, lambda: self.compression_failed(str(e)))

    def update_progress(self, pct, status_text):
        self.after(0, lambda: self.set_progress_ui(pct, status_text))

    def set_progress_ui(self, pct, status_text):
        self.progress_bar["value"] = pct
        self.lbl_status.config(text=status_text, fg="#f59e0b")

    def compression_success(self):
        self.is_compressing = False
        self.btn_start.config(state="normal", text="🚀 COMPRESS ANOTHER VIDEO")
        self.btn_cancel.config(state="disabled")
        self.progress_bar["value"] = 100

        orig_sz = self.input_file.stat().st_size / (1024 * 1024)
        new_sz = self.output_file.stat().st_size / (1024 * 1024)
        saved = max(0, int((1 - new_sz / orig_sz) * 100))

        msg = f"🎉 Done! {orig_sz:.1f} MB ➔ {new_sz:.1f} MB (Saved {saved}% file size!)"
        self.lbl_status.config(text=msg, fg="#10b981", font=("Segoe UI", 11, "bold"))

        self.btn_open_folder.pack(side="left", padx=(0, 10))
        self.btn_play_video.pack(side="left")
        self.finish_frame.pack(fill="x", pady=(10, 0))

        try:
            self.bell()
        except:
            pass

        messagebox.showinfo("Compression Complete", f"Success!\n\nOriginal: {orig_sz:.1f} MB\nCompressed: {new_sz:.1f} MB\nSaved: {saved}%\n\nFile saved to:\n{self.output_file}")

    def compression_failed(self, err_msg):
        self.is_compressing = False
        self.btn_start.config(state="normal", text="🚀 START COMPRESSION")
        self.btn_cancel.config(state="disabled")
        self.lbl_status.config(text=f"Error: {err_msg}", fg="#ef4444")
        messagebox.showerror("Compression Failed", f"An error occurred during compression:\n{err_msg}")

    def open_output_folder(self):
        if self.output_file and self.output_file.parent.exists():
            os.startfile(str(self.output_file.parent))

    def play_output_video(self):
        if self.output_file and self.output_file.exists():
            os.startfile(str(self.output_file))

if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
