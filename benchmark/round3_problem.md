# Blind benchmark round 3: Graph-walk vs flat RAG — Multi-turn token accumulation

You are an independent measurer. Follow the problem exactly and **return only the table in Section 7**. No long explanations, no comparing rounds yourself. No sample answer.

## 1. Goal

This round tests a specific hypothesis: **does graph-based history compression keep token_in growth sublinear across a 4-turn conversation chain, compared to flat history accumulation?**

Rounds 1 and 2 measured single-shot retrieval. This round measures the same codebase (Pipeline V11) but across a conversation chain where each question builds on the previous answer. The critical measurement is **token_in at each turn**, not just the total.

## 2. The two methods

**Method A — Flat accumulation (baseline):**
- Turn 1: load up to 5 relevant code chunks + Q1. Answer.
- Turn 2: resend ALL of Turn 1 context (chunks + Q1 + your A1) + load up to 5 new relevant chunks for Q2 + Q2. Answer.
- Turn 3: resend ALL of Turn 1+2 context + load up to 5 new chunks for Q3 + Q3. Answer.
- Turn 4: resend ALL of Turn 1+2+3 context + load up to 5 new chunks for Q4 + Q4. Answer.

**token_in at each turn = all tokens loaded into context for that turn, including accumulated history.**

**Method B — Graph signature (compact history):**
- Turn 1: load edge list + open only `evidence` lines relevant to Q1 + Q1. Answer. **Then compress the answer into a graph signature** (see Section 3 for format).
- Turn 2: load edge list + relevant evidence for Q2 + Q2 + **only the graph signature from Turn 1** (not the full A1 text). Answer. Append new graph signature.
- Turn 3: load edge list + relevant evidence for Q3 + Q3 + **graph signatures from Turns 1–2**. Answer. Append new signature.
- Turn 4: load edge list + relevant evidence for Q4 + Q4 + **graph signatures from Turns 1–3**. Answer.

**token_in at each turn = edge list + evidence lines opened + question + accumulated signatures (not full prior answers).**

**The two methods run INDEPENDENTLY — no result leaks between them.**

## 3. Graph signature format (Method B only)

After answering each turn in Method B, compress your answer into a graph signature:

```
TURN_N_SIG: [node_ids_visited] → [finding_in_max_15_words]
```

Example:
```
TURN_1_SIG: [mod:transcribe, env:CONDITION_ON_PREVIOUS_TEXT, env:COMPRESSION_RATIO_THRESHOLD] → condition_on_previous_text=False prevents hallucination loops in long files
```

Rules:
- Node IDs must be from the graph in Section 6.
- Finding must be ≤ 15 words.
- The signature replaces the full answer in subsequent turns — do NOT carry forward full answer text.

## 4. The four questions (conversation chain)

The questions form a chain: each follow-up is a natural next question after the previous answer.

**Q1:** What mechanisms does the pipeline use to prevent or reduce hallucination in the transcription output? List all you find.

**Q2 (follow-up to Q1):** For the mechanisms you found in Q1 — which ones are configurable by the user at runtime (via environment variables or GUI), and what are their default values?

**Q3 (follow-up to Q2):** Among the configurable parameters from Q2 — if a user wants to maximally reduce hallucination (prioritizing accuracy over speed), which parameters should they change, and in which direction?

**Q4 (follow-up to Q3):** If the user applies those changes from Q3, which other pipeline components or modules would be affected, and how?


## 5. Codebase (full, for Method A to chunk)

> **Note:** This is the real Pipeline V11 source, kept verbatim. Code comments and log strings are in Vietnamese — intentionally NOT translated. The code logic reads regardless of comment language.


> **Note:** This is the real Pipeline V11 source, kept verbatim. Code comments and log strings are in Vietnamese (the original codebase language) and are intentionally NOT translated — each graph edge's `evidence` (file:line) must match this exact source, which is what makes the benchmark verifiable. The code logic reads regardless of comment language; the questions and framing above are in English.

### `main.py`
```python
"""
main.py
-------
GUI tkinter - Transcription Pipeline
"""

import os
import sys

# Set model path truoc khi import bat ky thu vien nao
# Khi chay tu .exe, models\ nam canh file .exe
if getattr(sys, 'frozen', False):
    # Dang chay tu .exe (PyInstaller)
    _base = os.path.dirname(sys.executable)
else:
    # Dang chay tu source
    _base = os.path.dirname(os.path.abspath(__file__))

_models_dir = os.path.join(_base, "models")
os.makedirs(_models_dir, exist_ok=True)

# Force tất cả HuggingFace/faster-whisper đều dùng cùng 1 thư mục models# Dùng [] thay vì setdefault để OVERRIDE kể cả khi biến đã tồn tại
os.environ["HF_HOME"]                    = _models_dir
os.environ["HF_DATASETS_CACHE"]          = _models_dir
os.environ["HUGGINGFACE_HUB_CACHE"]      = os.path.join(_models_dir, "hub")
os.environ["TRANSFORMERS_CACHE"]         = os.path.join(_models_dir, "hub")
os.environ["HF_HUB_CACHE"]              = os.path.join(_models_dir, "hub")
os.environ["CT2_VERBOSE"]               = "0"
# Tắt warning symlinks trên Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import threading
import time
import queue
import logging
import subprocess
import tempfile
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, OptionMenu,
    Text, Scrollbar, filedialog, messagebox, END, DISABLED, NORMAL,
    WORD, RIGHT, Y, BOTH, X, LEFT, BooleanVar, Checkbutton
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Scan model + detect hardware khi khởi động ───────────────────────────────
_hw_profile = None   # Cache hardware profile

def _scan_models_on_startup():
    """Quét tất cả model có sẵn trên máy khi app khởi động."""
    try:
        from pipeline.model_locator import scan_available
        available = scan_available()
        if available:
            logger.info(f"Tìm thấy {len(available)} model: {', '.join(available.keys())}")
        return available
    except Exception as e:
        logger.warning(f"Scan model lỗi: {e}")
        return {}


def _detect_hardware():
    """Auto-detect hardware và apply profile."""
    global _hw_profile
    try:
        from pipeline.hardware_detect import detect, apply_to_env
        _hw_profile = detect()
        apply_to_env(_hw_profile)
        return _hw_profile
    except Exception as e:
        logger.warning(f"Hardware detect lỗi: {e}")
        return None


def _ask_model_path_gui(model_name: str) -> str | None:
    """
    Hỏi người dùng chỉ đường thư mục chứa model qua dialog.
    Gọi khi model_locator không tìm thấy tự động.
    """
    from tkinter import messagebox, filedialog
    answer = messagebox.askyesno(
        "Không tìm thấy model",
        f"Không tìm thấy model '{model_name}' tự động.\n\n"
        f"Bạn có muốn chỉ đường thủ công không?\n"
        f"(Chọn thư mục chứa model.bin)"
    )
    if not answer:
        return None
    path = filedialog.askdirectory(
        title=f"Chọn thư mục chứa model '{model_name}'",
        initialdir=str(Path.home() / ".cache" / "huggingface" / "hub")
    )
    return path if path else None


DEFAULT_MODEL   = os.getenv("WHISPER_MODEL", "medium")
DEFAULT_LANG    = os.getenv("WHISPER_LANGUAGE", "vi")
DEFAULT_DEVICE  = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DEFAULT_OUT_DIR = os.getenv("OUTPUT_DIR", "")
MODELS          = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
LANGUAGES       = ["vi", "en", "auto"]
CHUNK_MINUTES   = 2    # phut moi chunk — toi uu cho tieng Viet (cu 10 phut qua dai)

# ── Cấu hình mở rộng ──────────────────────────────────────────────────────────
DENOISE_ENABLED  = os.getenv("DENOISE_ENABLED", "true").lower() == "true"
DENOISE_LEVEL    = int(os.getenv("DENOISE_LEVEL", "2"))
LLM_ENABLED      = os.getenv("LLM_ENABLED", "true").lower() == "true"
LLM_MODEL        = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
LLM_DOMAIN       = os.getenv("LLM_DOMAIN", "")
SILENCE_THRESH   = float(os.getenv("SILENCE_THRESHOLD_DB", "-35"))
SILENCE_MIN_SEC  = float(os.getenv("SILENCE_MIN_SEC", "0.5"))
# ── VAD — kiểm soát bao nhiêu audio bị lọc bỏ ────────────────────────────────
VAD_THRESHOLD     = float(os.getenv("VAD_THRESHOLD",     "0.3"))
VAD_MIN_SILENCE   = int(os.getenv("VAD_MIN_SILENCE_MS",  "300"))
VAD_SPEECH_PAD    = int(os.getenv("VAD_SPEECH_PAD_MS",   "400"))

# ── Anti-hallucination (từ whisper_watcher v5) ────────────────────────────────
COND_ON_PREV      = os.getenv("CONDITION_ON_PREVIOUS_TEXT", "false").lower() == "true"
COMPRESS_RATIO    = float(os.getenv("COMPRESSION_RATIO_THRESHOLD", "2.4"))
LOG_PROB_THRESH   = float(os.getenv("LOG_PROB_THRESHOLD",          "-1.0"))
NO_SPEECH_THRESH  = float(os.getenv("NO_SPEECH_THRESHOLD",         "0.6"))
REPEAT_PENALTY    = float(os.getenv("REPETITION_PENALTY",          "1.2"))

# ── Logging ───────────────────────────────────────────────────────────────────
log_queue: queue.Queue = queue.Queue()

class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.put(self.format(record))

_qh = QueueHandler()
_qh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                                    datefmt="%H:%M:%S"))
logging.root.addHandler(_qh)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("main")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _get_duration(audio_path: Path) -> float:
    """Lấy duration bằng ffprobe."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ], capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _extract_chunk(audio_path: Path, start_sec: float, duration_sec: float) -> tuple:
    """Cắt 1 đoạn audio bằng ffmpeg, trả về (tmp_path, cleanup_needed)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    ret = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-t",  str(duration_sec),
        "-i",  str(audio_path),
        "-ar", "16000", "-ac", "1", "-f", "wav", tmp.name
    ], capture_output=True, text=True)
    if ret.returncode != 0:
        logger.error(f"ffmpeg chunk failed: {ret.stderr[-200:]}")
        return None, False
    return Path(tmp.name), True


def _detect_silence_boundaries(
    audio_path: Path,
    chunk_minutes: int       = CHUNK_MINUTES,
    silence_thresh_db: float = SILENCE_THRESH,
    silence_min_sec: float   = SILENCE_MIN_SEC,
) -> list:
    """
    Tính danh sách (start, end) để cắt audio tại điểm lặng.
    Thay vì cắt cứng mỗi N phút, tìm điểm lặng GẦN NHẤT với mốc N phút.
    Tránh cắt giữa câu.
    Returns: list[(start_sec, end_sec)]
    """
    total = _get_duration(audio_path)
    if total <= 0:
        return [(0.0, -1)]

    chunk_sec = chunk_minutes * 60

    # Dùng ffmpeg silencedetect để tìm tất cả điểm lặng
    ret = subprocess.run([
        "ffmpeg", "-i", str(audio_path),
        "-af", f"silencedetect=noise={silence_thresh_db}dB:d={silence_min_sec}",
        "-f", "null", "-"
    ], capture_output=True, text=True)

    # Parse output lấy silence_end (điểm kết thúc lặng = điểm tốt để cắt)
    silence_points = []
    for line in ret.stderr.splitlines():
        if "silence_end" in line:
            try:
                val = float(line.split("silence_end:")[1].split()[0])
                silence_points.append(val)
            except Exception:
                pass

    if not silence_points:
        # Không tìm thấy điểm lặng → fallback cắt cứng
        logger.warning("Không phát hiện silence → cắt cứng theo thời gian")
        boundaries = []
        start = 0.0
        while start < total:
            end = min(start + chunk_sec, total)
            boundaries.append((start, end))
            start = end
        return boundaries

    # Tìm điểm lặng gần nhất với mỗi mốc chunk
    boundaries = []
    start = 0.0
    while start < total - 1.0:
        target = start + chunk_sec
        if target >= total:
            boundaries.append((start, total))
            break

        # Tìm silence_end gần target nhất, trong cửa sổ ±30 giây
        best = None
        best_dist = float("inf")
        for sp in silence_points:
            if sp <= start:
                continue
            dist = abs(sp - target)
            if dist < best_dist and dist < 30:
                best_dist = dist
                best = sp

        if best is None:
            # Không có silence gần → cắt cứng tại target
            best = target

        boundaries.append((start, best))
        logger.debug(f"  Chunk: {start/60:.1f} → {best/60:.1f} phút")
        start = best

    if not boundaries:
        boundaries = [(0.0, total)]

    logger.info(f"Chia thành {len(boundaries)} chunk tại điểm lặng")
    return boundaries


def _run_pipeline(audio_path: Path, model: str, language: str,
                  device: str, compute: str, output_dir: Path | None,
                  diarize: bool = False, export_srt: bool = False,
                  chunk_mode: bool = True):

    from pipeline.audio       import inspect
    from pipeline.transcribe  import run as transcribe
    from pipeline.diarize     import run as do_diarize
    from pipeline.export      import export_chunk, export_final
    from pipeline.denoise     import run as denoise
    from pipeline.postprocess import run as postprocess

    info = inspect(audio_path)
    if not info.ok:
        logger.error(f"Audio khong hop le: {info.error}")
        return

    lang_arg  = None if language == "auto" else language
    out_dir   = output_dir
    total_dur = _get_duration(audio_path)

    # ── Bước 1: Denoise toàn bộ file trước khi chunk ─────────────────────
    denoise_engine = os.getenv("HW_DENOISE_ENGINE", "ffmpeg")
    denoised_path, denoise_cleanup = denoise(
        audio_path, level=DENOISE_LEVEL, engine=denoise_engine
    ) if DENOISE_ENABLED else (audio_path, False)

    if chunk_mode and total_dur > CHUNK_MINUTES * 60:
        # ── Chunk mode ────────────────────────────────────────────────────
        logger.info(f"File dai {total_dur/60:.1f} phut -> xu ly theo chunk ~{CHUNK_MINUTES} phut")

        # ── Bước 2: Tính boundaries tại điểm lặng ────────────────────────
        boundaries = _detect_silence_boundaries(denoised_path)
        all_segments = []

        for chunk_idx, (start, end) in enumerate(boundaries, start=1):
            duration = end - start
            logger.info(f"--- Chunk {chunk_idx}/{len(boundaries)}: {start/60:.1f} - {end/60:.1f} phut ---")

            wav_path, cleanup = _extract_chunk(denoised_path, start, duration)
            if wav_path is None:
                continue

            try:
                # Transcribe chunk
                segments = transcribe(
                    audio_path                  = wav_path,
                    model_name                  = model,
                    language                    = lang_arg,
                    device                      = device,
                    compute_type                = compute,
                    vad_threshold               = VAD_THRESHOLD,
                    vad_min_silence_ms          = VAD_MIN_SILENCE,
                    vad_speech_pad_ms           = VAD_SPEECH_PAD,
                    ask_callback                = _ask_model_path_gui,
                    condition_on_previous_text  = COND_ON_PREV,
                    compression_ratio_threshold = COMPRESS_RATIO,
                    log_prob_threshold          = LOG_PROB_THRESH,
                    no_speech_threshold         = NO_SPEECH_THRESH,
                    repetition_penalty          = REPEAT_PENALTY,
                )

                # Shift timestamps về đúng vị trí trong file gốc
                for seg in segments:
                    seg.start += start
                    seg.end   += start

                # ── Bước 3: LLM post-process ──────────────────────────────
                segments = postprocess(
                    segments    = segments,
                    enabled     = LLM_ENABLED,
                    model       = LLM_MODEL,
                    domain_hint = LLM_DOMAIN,
                )

                # Diarize chunk
                if diarize:
                    segments = do_diarize(
                        audio_path = wav_path,
                        segments   = segments,
                        enabled    = True,
                    )

                # Xuất ngay chunk này
                if segments:
                    export_chunk(
                        segments        = segments,
                        audio_path      = audio_path,
                        chunk_index     = chunk_idx,
                        chunk_start_sec = start,
                        chunk_end_sec   = end,
                        output_dir      = out_dir,
                        language        = language,
                        export_srt      = export_srt,
                    )
                    all_segments.extend(segments)
                    logger.info(f"Chunk {chunk_idx} xong → có thể dùng file _part{chunk_idx:02d}.docx ngay")

            finally:
                if cleanup and wav_path.exists():
                    wav_path.unlink()

        # Xuất file cuối gộp tất cả
        if all_segments:
            logger.info("Gộp tất cả chunk thành file cuối...")
            results = export_final(
                all_segments = all_segments,
                audio_path   = audio_path,
                output_dir   = out_dir,
                language     = language,
                export_srt   = export_srt,
            )
            logger.info(f"Hoàn tất! File đầy đủ: {results['docx'].name}")

            # Xóa các file chunk riêng lẻ
            for i in range(1, len(boundaries) + 1):
                for ext in ["docx", "srt"]:
                    p = (out_dir or audio_path.parent) / f"{audio_path.stem}_part{i:02d}.{ext}"
                    if p.exists():
                        p.unlink()
            logger.info("Đã xóa các file chunk tạm thời.")

    else:
        # ── Single mode (file ngắn) ───────────────────────────────────────
        from pipeline.export import export_all
        segments = transcribe(
            audio_path                  = denoised_path,
            model_name                  = model,
            language                    = lang_arg,
            device                      = device,
            compute_type                = compute,
            vad_threshold               = VAD_THRESHOLD,
            vad_min_silence_ms          = VAD_MIN_SILENCE,
            vad_speech_pad_ms           = VAD_SPEECH_PAD,
            ask_callback                = _ask_model_path_gui,
            condition_on_previous_text  = COND_ON_PREV,
            compression_ratio_threshold = COMPRESS_RATIO,
            log_prob_threshold          = LOG_PROB_THRESH,
            no_speech_threshold         = NO_SPEECH_THRESH,
            repetition_penalty          = REPEAT_PENALTY,
        )
        if not segments:
            logger.warning("Khong nhan duoc segment nao")
            return

        # ── Bước 3: LLM post-process ──────────────────────────────────────
        segments = postprocess(
            segments    = segments,
            enabled     = LLM_ENABLED,
            model       = LLM_MODEL,
            domain_hint = LLM_DOMAIN,
        )

        segments = do_diarize(audio_path=denoised_path, segments=segments, enabled=diarize)
        results  = export_all(segments, audio_path, out_dir, language, export_srt)
        logger.info(f"Hoan tat: {audio_path.name}")
        for fmt, path in results.items():
            logger.info(f"  -> {fmt.upper()}: {path}")

    # Cleanup file denoise tạm
    finally_cleanup = denoise_cleanup and denoised_path != audio_path
    if finally_cleanup and denoised_path.exists():
        denoised_path.unlink()
        logger.debug("Đã xóa file denoise tạm")


# ── Watcher ───────────────────────────────────────────────────────────────────

class FolderWatcher:
    def __init__(self, folder, model, language, device, compute,
                 output_dir, diarize=False, export_srt=False, chunk_mode=True):
        self.folder     = folder
        self.model      = model
        self.language   = language
        self.device     = device
        self.compute    = compute
        self.output_dir = output_dir
        self.diarize    = diarize
        self.export_srt = export_srt
        self.chunk_mode = chunk_mode
        self._observer  = None

    def start(self):
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        from pipeline.utils import is_audio_file
        watcher = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                path = Path(event.src_path)
                if is_audio_file(path):
                    time.sleep(1.5)
                    logger.info(f"Phat hien file moi: {path.name}")
                    threading.Thread(target=watcher._process, args=(path,), daemon=True).start()

        self._observer = Observer()
        self._observer.schedule(Handler(), str(self.folder), recursive=False)
        self._observer.start()
        logger.info(f"Dang watch: {self.folder}")

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("Watcher da dung.")

    def _process(self, path):
        try:
            _run_pipeline(
                audio_path  = path,
                model       = self.model,
                language    = self.language,
                device      = self.device,
                compute     = self.compute,
                output_dir  = self.output_dir,
                diarize     = self.diarize,
                export_srt  = self.export_srt,
                chunk_mode  = self.chunk_mode,
            )
        except Exception as e:
            logger.error(f"Loi: {e}", exc_info=True)


# ── GUI ───────────────────────────────────────────────────────────────────────

class App(Tk):

    def __init__(self):
        super().__init__()
        self.title("Transcription Pipeline")
        self.resizable(True, True)
        self.minsize(760, 540)
        self._watcher = None
        self._build_ui()
        self._poll_log()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 3}

        # ── Hardware status bar ──────────────────────────────────────────────
        hw_fr = Frame(self, bg="#2c3e50"); hw_fr.pack(fill=X)

        # Label chế độ tự động
        self.lbl_hw_mode = Label(
            hw_fr, text="⚙ Đang phát hiện cấu hình...",
            bg="#2c3e50", fg="#ecf0f1", font=("Consolas", 9), anchor="w"
        )
        self.lbl_hw_mode.pack(side=LEFT, padx=8, pady=4)

        # Nút override thủ công
        Label(hw_fr, text="Override:", bg="#2c3e50", fg="#bdc3c7",
              font=("Consolas", 9)).pack(side=LEFT, padx=(20,2))
        self.var_hw_override = StringVar(value="auto")
        hw_menu = OptionMenu(hw_fr, self.var_hw_override,
                             "auto", "basic", "standard", "full",
                             command=self._on_hw_override)
        hw_menu.config(bg="#34495e", fg="white", activebackground="#1abc9c",
                       relief="flat", highlightthickness=0, font=("Consolas", 9))
        hw_menu.pack(side=LEFT)

        # Update hardware info sau 100ms (không block GUI)
        self.after(100, self._update_hw_display)

        # Input file
        fr = Frame(self); fr.pack(fill=X, **pad)
        Label(fr, text="File âm thanh:", width=14, anchor="w").pack(side=LEFT)
        self.var_input = StringVar()
        Entry(fr, textvariable=self.var_input, width=50, state="readonly").pack(side=LEFT, padx=4)
        Button(fr, text="Chọn file…", command=self._browse_input).pack(side=LEFT)

        # Output folder
        fr = Frame(self); fr.pack(fill=X, **pad)
        Label(fr, text="Output Folder:", width=14, anchor="w").pack(side=LEFT)
        self.var_outdir = StringVar(value=DEFAULT_OUT_DIR)
        Entry(fr, textvariable=self.var_outdir, width=50).pack(side=LEFT, padx=4)
        Button(fr, text="Browse…", command=self._browse_outdir).pack(side=LEFT)
        Label(fr, text="(trống = cùng folder audio)", fg="gray").pack(side=LEFT, padx=4)

        # Model / Lang / Device / Compute
        fr = Frame(self); fr.pack(fill=X, **pad)
        Label(fr, text="Model:").pack(side=LEFT)
        self.var_model = StringVar(value=DEFAULT_MODEL)
        OptionMenu(fr, self.var_model, *MODELS).pack(side=LEFT, padx=4)

        Label(fr, text="Language:").pack(side=LEFT, padx=(10,0))
        self.var_lang = StringVar(value=DEFAULT_LANG)
        OptionMenu(fr, self.var_lang, *LANGUAGES).pack(side=LEFT, padx=4)

        Label(fr, text="Device:").pack(side=LEFT, padx=(10,0))
        self.var_device = StringVar(value=DEFAULT_DEVICE)
        OptionMenu(fr, self.var_device, "cpu", "cuda").pack(side=LEFT, padx=4)

        Label(fr, text="Compute:").pack(side=LEFT, padx=(10,0))
        self.var_compute = StringVar(value=DEFAULT_COMPUTE)
        OptionMenu(fr, self.var_compute, "int8", "float16", "float32").pack(side=LEFT, padx=4)

        # Options checkboxes
        fr = Frame(self); fr.pack(fill=X, **pad)
        self.var_diarize = BooleanVar(value=False)
        self.var_srt     = BooleanVar(value=False)
        self.var_chunk   = BooleanVar(value=True)
        Checkbutton(fr, text="Phân tách người nói",
                    variable=self.var_diarize).pack(side=LEFT)
        Checkbutton(fr, text="Xuất thêm file SRT",
                    variable=self.var_srt).pack(side=LEFT, padx=(16,0))
        Checkbutton(fr, text=f"Xử lý từng {CHUNK_MINUTES} phút (xuất sớm)",
                    variable=self.var_chunk).pack(side=LEFT, padx=(16,0))

        # Buttons
        fr = Frame(self); fr.pack(fill=X, **pad)
        self.btn_run = Button(fr, text="▶  Chạy", bg="#2ecc71", fg="white",
                              width=14, command=self._run_single)
        self.btn_run.pack(side=LEFT, padx=4)
        self.lbl_status = Label(fr, text="Chưa chọn file.", fg="gray")
        self.lbl_status.pack(side=LEFT, padx=8)

        # Log
        fr = Frame(self); fr.pack(fill=BOTH, expand=True, padx=8, pady=(4,8))
        Label(fr, text="Log:", anchor="w").pack(fill=X)
        self.txt_log = Text(fr, wrap=WORD, state=DISABLED,
                            bg="#1e1e1e", fg="#d4d4d4",
                            font=("Consolas", 9), relief="flat")
        sb = Scrollbar(fr, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.txt_log.pack(fill=BOTH, expand=True)
        Button(fr, text="Xóa log", command=self._clear_log).pack(anchor="e", pady=2)

    def _browse_input(self):
        file = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[("Audio/Video", "*.mp3 *.mp4 *.wav *.m4a *.ogg *.flac *.aac *.mkv"),
                       ("Tất cả", "*.*")]
        )
        if file:
            self.var_input.set(file)
            self.lbl_status.config(text=f"Sẵn sàng: {Path(file).name}", fg="gray")

    def _browse_outdir(self):
        d = filedialog.askdirectory()
        if d: self.var_outdir.set(d)

    def _get_outdir(self):
        v = self.var_outdir.get().strip()
        return Path(v) if v else None

    def _run_single(self):
        file = self.var_input.get().strip()
        if not file or not Path(file).exists():
            messagebox.showerror("Lỗi", "Hãy chọn file âm thanh trước.")
            return
        self.btn_run.config(state=DISABLED)
        self.lbl_status.config(text=f"Đang xử lý: {Path(file).name}", fg="orange")

        def _done():
            self.btn_run.config(state=NORMAL)
            self.lbl_status.config(text="Xong!", fg="#2ecc71")

        def _run():
            try:
                _run_pipeline(
                    audio_path  = Path(file),
                    model       = self.var_model.get(),
                    language    = self.var_lang.get(),
                    device      = self.var_device.get(),
                    compute     = self.var_compute.get(),
                    output_dir  = self._get_outdir(),
                    diarize     = self.var_diarize.get(),
                    export_srt  = self.var_srt.get(),
                    chunk_mode  = self.var_chunk.get(),
                )
            finally:
                self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _clear_log(self):
        self.txt_log.config(state=NORMAL)
        self.txt_log.delete("1.0", END)
        self.txt_log.config(state=DISABLED)

    def _poll_log(self):
        try:
            while True:
                msg = log_queue.get_nowait()
                self.txt_log.config(state=NORMAL)
                self.txt_log.insert(END, msg + "\n")
                self.txt_log.see(END)
                self.txt_log.config(state=DISABLED)
        except queue.Empty:
            pass
        self.after(200, self._poll_log)

    def _update_hw_display(self):
        """Chạy hardware detect trong thread, cập nhật GUI sau."""
        def _detect():
            profile = _detect_hardware()
            if profile:
                self.after(0, lambda: self._apply_hw_profile(profile))

        import threading
        threading.Thread(target=_detect, daemon=True).start()

    def _apply_hw_profile(self, profile, from_override=False):
        """Apply hardware profile vào GUI."""
        from pipeline.hardware_detect import apply_to_env
        apply_to_env(profile)

        # Cập nhật label
        mode_colors = {
            "basic":    "#e67e22",
            "standard": "#27ae60",
            "full":     "#2980b9",
        }
        color = mode_colors.get(profile.mode, "#ecf0f1")
        self.lbl_hw_mode.config(
            text=f"{profile.mode_label}  |  {profile.engines_label}  |  "
                 f"RAM {profile.ram_gb:.0f}GB"
                 + (f"  |  GPU {profile.gpu_name}" if profile.has_gpu else ""),
            fg=color
        )

        # Tự động set device/compute theo profile (nếu không override thủ công)
        if not from_override:
            self.var_device.set(profile.device)
            self.var_compute.set(profile.compute_type)
            if profile.diarize:
                self.var_diarize.set(True)

    def _on_hw_override(self, choice: str):
        """Người dùng chọn override chế độ thủ công."""
        if choice == "auto":
            self._update_hw_display()
            return

        from pipeline.hardware_detect import HardwareProfile, apply_to_env
        profile = HardwareProfile()

        if choice == "basic":
            profile.mode           = "basic"
            profile.device         = "cpu"
            profile.compute_type   = "int8"
            profile.asr_engine     = "faster-whisper"
            profile.denoise_engine = "ffmpeg"
            profile.diarize        = False

        elif choice == "standard":
            profile.mode           = "standard"
            profile.device         = "cpu"
            profile.compute_type   = "int8"
            profile.asr_engine     = "faster-whisper"
            profile.denoise_engine = "noisereduce"
            profile.diarize        = False

        elif choice == "full":
            profile.mode           = "full"
            profile.device         = "cuda"
            profile.compute_type   = "float16"
            profile.asr_engine     = "whisperx"
            profile.denoise_engine = "noisereduce"
            profile.diarize        = True

        self._apply_hw_profile(profile, from_override=True)

    def on_close(self):
        self.destroy()


if __name__ == "__main__":
    print("Đang kiểm tra cấu hình...")
    _scan_models_on_startup()  # Quét model — kết quả lưu vào models.json

    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

```

### `download_models.py`
```python
"""
download_models.py
------------------
Tải model faster-whisper VÀ pyannote về thư mục models local.

Thông minh hơn:
  - Kiem tra model da co trong models/ chua -> khong download lai
  - Neu model da co trong cache Windows (~/.cache/huggingface) -> copy ve models/
  - Chỉ download từ internet khi thực sự chưa có ở đâu cả
  - Tắt warning symlinks Windows

Chạy:
  python download_models.py              ← model trong .env
  python download_models.py medium       ← chỉ medium
  python download_models.py all          ← tất cả model
  python download_models.py status       ← xem model nào đã có
  python download_models.py small large-v2  ← nhiều model
"""

import os
import sys
import shutil
from pathlib import Path

# ── Setup path TRƯỚC KHI import huggingface ───────────────────────────────────
_base       = os.path.dirname(os.path.abspath(__file__))
_models_dir = os.path.join(_base, "models")
_hub_dir    = os.path.join(_models_dir, "hub")
os.makedirs(_hub_dir, exist_ok=True)

# Force tất cả cache về models\ — phải set TRƯỚC khi import bất kỳ thứ gì
os.environ["HF_HOME"]                         = _models_dir
os.environ["HF_DATASETS_CACHE"]               = _models_dir
os.environ["HUGGINGFACE_HUB_CACHE"]           = _hub_dir
os.environ["TRANSFORMERS_CACHE"]              = _hub_dir
os.environ["HF_HUB_CACHE"]                   = _hub_dir
os.environ["CT2_VERBOSE"]                     = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL_NAME = os.getenv("WHISPER_MODEL", "medium")
DEVICE     = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE    = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
HF_TOKEN   = os.getenv("HF_TOKEN", "")

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# Cache mặc định của HuggingFace trên hệ thống
_SYS_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
_SYS_FW_CACHE = Path.home() / ".cache" / "faster_whisper"


def _find_in_system_cache(model_name: str):
    """Tìm model đã có trong cache hệ thống. Trả về Path cache root hoặc None."""
    folder_name = f"models--Systran--faster-whisper-{model_name}"
    for cache_root in [_SYS_HF_CACHE, _SYS_FW_CACHE]:
        candidate = cache_root / folder_name
        if candidate.exists() and list(candidate.rglob("model.bin")):
            return cache_root
    return None


def _copy_from_system_cache(model_name: str, src_cache: Path) -> bool:
    """Copy model từ cache hệ thống vào models\\hub\\  của project."""
    folder_name = f"models--Systran--faster-whisper-{model_name}"
    src = src_cache / folder_name
    dst = Path(_hub_dir) / folder_name
    if dst.exists():
        return True
    print(f"  [*] Tìm thấy trong cache hệ thống → copy về project (không cần internet)")
    print(f"      {src}")
    print(f"      → {dst}")
    try:
        shutil.copytree(str(src), str(dst))
        print(f"  [OK] Copy xong!")
        return True
    except Exception as e:
        print(f"  [WARN] Copy thất bại: {e} — sẽ download bình thường")
        return False


def _model_exists_local(model_name: str) -> bool:
    """Kiểm tra model đã có đầy đủ trong models\\hub\\  chưa."""
    folder_name = f"models--Systran--faster-whisper-{model_name}"
    model_dir   = Path(_hub_dir) / folder_name
    if not model_dir.exists():
        return False
    return len(list(model_dir.rglob("model.bin"))) > 0


def download_whisper(model_name: str):
    """
    Đảm bảo model có trong models\\hub\\ .
    Thứ tự: local → system cache (copy) → internet (download).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[ERROR] faster-whisper chưa cài. Chạy install.bat trước.")
        sys.exit(1)

    print(f"\n{'='*52}")
    print(f"  Model: {model_name}  ({DEVICE}/{COMPUTE})")
    print(f"{'='*52}")

    # 1. Đã có trong project rồi
    if _model_exists_local(model_name):
        print(f"  [OK] Đã có trong models\\hub\\  — không cần làm gì.")
        return

    # 2. Có trong cache hệ thống → copy
    sys_cache = _find_in_system_cache(model_name)
    if sys_cache:
        if _copy_from_system_cache(model_name, sys_cache):
            return

    # 3. Download từ internet
    sizes = {"tiny":"~150MB","base":"~300MB","small":"~500MB",
             "medium":"~1.5GB","large-v2":"~3GB","large-v3":"~3GB"}
    print(f"  [*] Chưa có ở đâu — download từ internet {sizes.get(model_name,'')}...")
    print(f"      Lưu vào: {_hub_dir}\n")
    try:
        model = WhisperModel(model_name, device=DEVICE, compute_type=COMPUTE)
        print(f"\n  [OK] Download '{model_name}' xong!")
        del model
    except Exception as e:
        print(f"\n  [ERROR] Download thất bại: {e}")
        sys.exit(1)


def download_pyannote():
    """Download pyannote nếu có HF_TOKEN."""
    if not HF_TOKEN or HF_TOKEN == "your_huggingface_token_here":
        print("\n[SKIP] HF_TOKEN chưa set — bỏ qua pyannote.")
        return
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        print("[ERROR] pyannote.audio chưa cài.")
        sys.exit(1)
    pyannote_dir = Path(_hub_dir) / "models--pyannote--speaker-diarization-3.1"
    if pyannote_dir.exists():
        print("\n[OK] pyannote model đã có — bỏ qua download.")
        return
    print("\n[*] Tải pyannote (~1GB)...")
    try:
        pipe = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", token=HF_TOKEN)
        print("[OK] pyannote sẵn sàng.")
        del pipe
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


def print_status():
    """In trạng thái tất cả model."""
    print(f"\n  Thư mục: {_models_dir}")
    print(f"  {'Model':<14} {'Trong project':<16} {'Cache hệ thống'}")
    print(f"  {'-'*48}")
    for m in AVAILABLE_MODELS:
        local  = "✓ Có" if _model_exists_local(m) else "✗ Chưa có"
        sys_c  = _find_in_system_cache(m)
        sys_st = f"✓ Có (sẽ copy)" if sys_c else "✗ Không có"
        print(f"  {m:<14} {local:<16} {sys_st}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print_status()
        download_whisper(MODEL_NAME)
        download_pyannote()
    elif args == ["all"]:
        print_status()
        for m in AVAILABLE_MODELS:
            download_whisper(m)
        download_pyannote()
    elif args == ["status"]:
        print_status()
        sys.exit(0)
    else:
        invalid = [a for a in args if a not in AVAILABLE_MODELS]
        if invalid:
            print(f"[ERROR] Model không hợp lệ: {', '.join(invalid)}")
            print(f"        Hỗ trợ: {', '.join(AVAILABLE_MODELS)}")
            sys.exit(1)
        print_status()
        for m in args:
            download_whisper(m)
        download_pyannote()

    print("=" * 52)
    print("Xong! Chạy: python main.py")

```

### `pipeline/audio.py`
```python
"""
pipeline/audio.py
-----------------
Kiểm tra và chuẩn bị file audio trước khi đưa vào Whisper.
- Validate định dạng
- Lấy metadata (duration, channels, sample rate) nếu pydub có sẵn
- Không convert — faster-whisper tự xử lý hầu hết định dạng qua ffmpeg
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .utils import get_logger, is_audio_file

logger = get_logger("audio")


@dataclass
class AudioInfo:
    path: Path
    duration_sec: Optional[float] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def inspect(audio_path: str | Path) -> AudioInfo:
    """
    Kiểm tra file audio.
    Trả về AudioInfo — nếu lỗi, .ok == False và .error có mô tả.
    """
    path = Path(audio_path)

    if not path.exists():
        return AudioInfo(path=path, error=f"File không tồn tại: {path}")

    if not is_audio_file(path):
        return AudioInfo(path=path, error=f"Định dạng không hỗ trợ: {path.suffix}")

    if path.stat().st_size == 0:
        return AudioInfo(path=path, error="File rỗng (0 bytes)")

    info = AudioInfo(path=path)

    # Cố lấy metadata bằng pydub (không bắt buộc)
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(path))
        info.duration_sec  = len(audio) / 1000.0
        info.channels      = audio.channels
        info.sample_rate   = audio.frame_rate
        logger.info(f"Audio OK: {path.name}  "
                    f"duration={info.duration_sec:.1f}s  "
                    f"ch={info.channels}  sr={info.sample_rate}Hz")
    except ImportError:
        logger.debug("pydub không có — bỏ qua metadata check")
    except Exception as e:
        logger.warning(f"Không lấy được metadata ({path.name}): {e}")

    return info

```

### `pipeline/denoise.py`
```python
"""
pipeline/denoise.py
-------------------
Lọc tạp âm (noise reduction) trước khi đưa vào Whisper.
Dùng ffmpeg afftdn + highpass/lowpass filter — chạy offline 100%, không cần cài thêm.

Chiến lược:
  - Mức 1 (nhẹ): chỉ highpass lọc tiếng ồn tần số thấp (điều hòa, quạt)
  - Mức 2 (trung bình, mặc định): afftdn + highpass/lowpass — tốt cho cuộc họp
  - Mức 3 (mạnh): afftdn noise reduction nặng hơn — khi phòng ồn nhiều

Nếu ffmpeg không hỗ trợ afftdn (version cũ), tự động fallback về highpass/lowpass.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from .utils import get_logger

logger = get_logger("denoise")


def _run_noisereduce(audio_path: Path, output_path: Path) -> bool:
    """
    Dùng noisereduce library — tốt hơn ffmpeg cho giọng nói.
    Chỉ chạy khi đã cài: pip install noisereduce
    """
    try:
        import noisereduce as nr
        import numpy as np
        import wave, array

        # Đọc WAV
        with wave.open(str(audio_path), 'rb') as wf:
            n_channels  = wf.getnchannels()
            sampwidth   = wf.getsampwidth()
            framerate   = wf.getframerate()
            raw_data    = wf.readframes(wf.getnframes())

        # Convert sang numpy
        dtype = np.int16 if sampwidth == 2 else np.int32
        data  = np.frombuffer(raw_data, dtype=dtype).astype(np.float32)
        if n_channels > 1:
            data = data.reshape(-1, n_channels).mean(axis=1)

        # Noise reduce — dùng 0.5s đầu làm noise sample
        noise_sample = data[:int(framerate * 0.5)]
        reduced      = nr.reduce_noise(
            y=data, sr=framerate,
            y_noise=noise_sample,
            prop_decrease=0.75,
            stationary=False,
        )

        # Ghi ra WAV
        reduced_int = (reduced * 32767).clip(-32768, 32767).astype(np.int16)
        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            wf.writeframes(reduced_int.tobytes())

        return True

    except ImportError:
        logger.warning("noisereduce chưa cài → fallback ffmpeg. Cài: pip install noisereduce")
        return False
    except Exception as e:
        logger.warning(f"noisereduce lỗi: {e} → fallback ffmpeg")
        return False


def run(
    audio_path:  Path,
    level:       int  = 2,     # 1=nhẹ, 2=trung bình, 3=mạnh
    engine:      str  = "auto", # "auto" / "ffmpeg" / "noisereduce"
    output_path: Path = None,
) -> tuple[Path, bool]:
    """
    Lọc tạp âm cho audio_path.

    Returns:
        (output_path, cần_xóa_sau)
        - Nếu denoise thành công → trả về path file đã lọc
        - Nếu lỗi → trả về audio_path gốc (không xóa)
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        out = Path(tmp.name)
        need_cleanup = True
    else:
        out = output_path
        need_cleanup = False

    # Đọc engine từ env nếu auto
    import os
    if engine == "auto":
        engine = os.getenv("HW_DENOISE_ENGINE", "ffmpeg")

    # Thử noisereduce nếu được yêu cầu
    if engine == "noisereduce":
        logger.info(f"Denoise noisereduce level={level}: {audio_path.name}")
        # Cần convert sang WAV 16kHz mono trước
        import subprocess as sp
        wav_tmp = Path(tempfile.mktemp(suffix=".wav"))
        sp.run([
            "ffmpeg", "-y", "-i", str(audio_path),
            "-ar", "16000", "-ac", "1", str(wav_tmp)
        ], capture_output=True)
        if wav_tmp.exists() and _run_noisereduce(wav_tmp, out):
            wav_tmp.unlink()
            logger.info(f"Denoise noisereduce OK → {out.name}")
            return out, need_cleanup
        if wav_tmp.exists():
            wav_tmp.unlink()
        logger.warning("noisereduce thất bại → fallback ffmpeg")

    # Chọn filter theo level
    if level == 1:
        # Nhẹ: chỉ lọc tần số thấp (quạt, điều hòa)
        af = "highpass=f=100,lowpass=f=8000"
    elif level == 3:
        # Mạnh: noise reduction nặng
        af = "afftdn=nf=-25,highpass=f=200,lowpass=f=7000"
    else:
        # Mặc định (level 2): cân bằng tốt cho cuộc họp
        af = "afftdn=nf=-20,highpass=f=150,lowpass=f=8000"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-af", af,
        "-ar", "16000", "-ac", "1", "-f", "wav",
        str(out)
    ]

    logger.info(f"Denoise level={level}: {audio_path.name}")
    ret = subprocess.run(cmd, capture_output=True, text=True)

    if ret.returncode != 0:
        # Thử fallback không dùng afftdn (ffmpeg version cũ)
        if "afftdn" in ret.stderr:
            logger.warning("afftdn không hỗ trợ, fallback về highpass/lowpass")
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-af", "highpass=f=150,lowpass=f=8000",
                "-ar", "16000", "-ac", "1", "-f", "wav",
                str(out)
            ]
            ret2 = subprocess.run(cmd_fallback, capture_output=True, text=True)
            if ret2.returncode != 0:
                logger.error(f"Denoise fallback thất bại: {ret2.stderr[-200:]}")
                if need_cleanup and out.exists():
                    out.unlink()
                return audio_path, False
            logger.info("Denoise fallback OK")
        else:
            logger.error(f"Denoise thất bại: {ret.stderr[-200:]}")
            if need_cleanup and out.exists():
                out.unlink()
            return audio_path, False

    # Kiểm tra output có hợp lệ không
    if not out.exists() or out.stat().st_size < 1000:
        logger.error("Denoise output rỗng hoặc quá nhỏ, dùng audio gốc")
        if need_cleanup and out.exists():
            out.unlink()
        return audio_path, False

    logger.info(f"Denoise OK → {out.name}")
    return out, need_cleanup

```

### `pipeline/diarize.py`
```python
"""
pipeline/diarize.py
-------------------
Phân tách người nói bằng pyannote.audio 3.1.
Gán SPEAKER_00, SPEAKER_01, … vào từng Segment theo overlap thời gian.

Yêu cầu:
  - pip install pyannote.audio
  - HF_TOKEN hợp lệ trong .env (chỉ cần lúc download model lần đầu)
  - Đã chạy download_models.py để cache model về local
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from .transcribe import Segment
from .utils import get_logger

logger = get_logger("diarize")


def _to_wav(audio_path: Path) -> tuple[Path, bool]:
    """
    Convert bất kỳ định dạng nào sang WAV 16kHz mono bằng ffmpeg.
    WAV native cũng convert lại để đảm bảo đúng sample rate.
    Trả về (wav_path, cần_xóa_sau)
    """
    import subprocess, tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    ret = subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", "-f", "wav", tmp.name
    ], capture_output=True, text=True)
    if ret.returncode != 0:
        logger.error(f"ffmpeg convert thất bại: {ret.stderr[-300:]}")
        return audio_path, False
    logger.info(f"Converted {audio_path.name} → WAV 16kHz tạm")
    return Path(tmp.name), True


def _assign_speakers(segments: list[Segment], diarization) -> list[Segment]:
    """
    Gán speaker cho mỗi segment bằng cách tìm turn overlap nhiều nhất.
    Dùng overlap thay vì midpoint — chính xác hơn với câu dài.
    """
    turns = list(diarization.itertracks(yield_label=True))

    for seg in segments:
        best_speaker = None
        best_overlap = 0.0

        for turn, _, speaker in turns:
            # Tính overlap giữa segment và turn
            overlap = min(seg.end, turn.end) - max(seg.start, turn.start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker

        seg.speaker = best_speaker or "UNKNOWN"

    return segments


def run(
    audio_path: str | Path,
    segments: list[Segment],
    enabled: bool = False,
    hf_token: Optional[str] = None,
) -> list[Segment]:
    """
    Gán speaker label vào segments.

    Args:
        audio_path: đường dẫn file audio
        segments:   list Segment từ transcribe.run()
        enabled:    True = chạy diarization, False = bỏ qua
        hf_token:   HF token (fallback về .env nếu None)

    Returns:
        list[Segment] với .speaker được gán (hoặc gốc nếu disabled)
    """
    if not enabled:
        logger.info("Diarization tắt — bỏ qua")
        return segments

    token = hf_token or os.getenv("HF_TOKEN", "")

    try:
        from pyannote.audio import Pipeline as PyAnnotePipeline
    except ImportError:
        logger.error("pyannote.audio chưa cài. Chạy: pip install pyannote.audio")
        return segments

    logger.info("Load pyannote speaker-diarization-3.1…")
    try:
        pipe = PyAnnotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=token if token else None
        )
    except Exception as e:
        logger.error(f"Không load được pyannote model: {e}")
        logger.error("Kiểm tra: đã chạy download_models.py chưa?")
        return segments

    logger.info(f"Đang diarize: {Path(audio_path).name}")
    wav_path, need_cleanup = _to_wav(Path(audio_path))
    try:
        diarization = pipe(str(wav_path))
    except Exception as e:
        logger.error(f"Diarization thất bại: {e}")
        return segments
    finally:
        if need_cleanup and wav_path.exists():
            wav_path.unlink()
            logger.debug("Đã xóa WAV tạm")

    segments = _assign_speakers(segments, diarization)

    # Đếm số speaker phát hiện được
    speakers = {s.speaker for s in segments if s.speaker and s.speaker != "UNKNOWN"}
    logger.info(f"Phát hiện {len(speakers)} người nói: {', '.join(sorted(speakers))}")

    return segments

```

### `pipeline/export.py`
```python
"""
pipeline/export.py
------------------
Xuất kết quả transcription ra .docx (mặc định) và .srt (tuỳ chọn).
Segment ngắn được gộp lại thành đoạn dài hơn để dễ đọc.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from .transcribe import Segment
from .utils import get_logger, seconds_to_srt_time, stem

logger = get_logger("export")


# ── Merge segments ────────────────────────────────────────────────────────────

def merge_segments(
    segments: list,
    min_duration: float = 4.0,
    max_duration: float = 30.0,
    pause_threshold: float = 1.5,
) -> list:
    if not segments:
        return segments

    from .transcribe import Segment as Seg
    merged = []
    current = Seg(
        start   = segments[0].start,
        end     = segments[0].end,
        text    = segments[0].text,
        speaker = segments[0].speaker,
    )

    for seg in segments[1:]:
        pause        = seg.start - current.end
        duration     = current.end - current.start
        same_speaker = (current.speaker == seg.speaker) or (not current.speaker and not seg.speaker)

        should_merge = (
            duration < min_duration
            and duration + (seg.end - seg.start) <= max_duration
            and pause < pause_threshold
            and same_speaker
        )

        if should_merge:
            current.end  = seg.end
            current.text = current.text.rstrip() + " " + seg.text.lstrip()
        else:
            merged.append(current)
            current = Seg(
                start   = seg.start,
                end     = seg.end,
                text    = seg.text,
                speaker = seg.speaker,
            )

    merged.append(current)
    logger.info(f"Merge: {len(segments)} segment -> {len(merged)} doan")
    return merged


# ── SRT ──────────────────────────────────────────────────────────────────────

def to_srt(segments, audio_path, output_dir=None, suffix=""):
    out_dir = output_dir or audio_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem(audio_path)}{suffix}.srt"

    lines = []
    for i, seg in enumerate(segments, start=1):
        sp = f"[{seg.speaker}] " if seg.speaker else ""
        lines.append(str(i))
        lines.append(f"{seconds_to_srt_time(seg.start)} --> {seconds_to_srt_time(seg.end)}")
        lines.append(f"{sp}{seg.text}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"SRT da luu: {out_path}")
    return out_path


# ── DOCX ─────────────────────────────────────────────────────────────────────

def to_docx(segments, audio_path, output_dir=None, language="vi", suffix="", chunk_label=""):
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        raise RuntimeError("python-docx chua duoc cai.")

    out_dir = output_dir or audio_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem(audio_path)}{suffix}.docx"

    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(12)

    # Tieu de
    title_text = f"Ban ghi: {stem(audio_path)}"
    if chunk_label:
        title_text += f"  -  {chunk_label}"
    h1 = doc.add_heading(title_text, level=1)
    h1.runs[0].font.size = Pt(14)
    h1.runs[0].font.bold = True
    h1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run(
        f"Ngon ngu: {language.upper()}   |   "
        f"So doan: {len(segments)}   |   "
        f"Xuat luc: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    doc.add_paragraph()

    # Bang
    has_speaker = any(s.speaker for s in segments)
    headers = ["#", "Thoi gian"]
    if has_speaker:
        headers.append("Nguoi noi")
    headers.append("Noi dung")

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        p  = hdr[i].paragraphs[0]
        r  = p.add_run(h)
        r.bold = True
        r.font.size = Pt(11)
        tc   = hdr[i]._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "2F5496")
        tcPr.append(shd)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for i, seg in enumerate(segments, start=1):
        row = table.add_row().cells
        row[0].text = str(i)
        t0 = seconds_to_srt_time(seg.start)[:8]
        t1 = seconds_to_srt_time(seg.end)[:8]
        row[1].text = f"{t0}\n{t1}"
        col = 2
        if has_speaker:
            row[col].text = seg.speaker or "-"
            col += 1
        row[col].text = seg.text
        for c in row:
            for para in c.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(10)

    doc.add_paragraph()

    # Toan van - nhom theo speaker
    h2 = doc.add_heading("Toan van", level=2)
    h2.runs[0].font.size = Pt(13)

    current_speaker = None
    current_texts   = []

    def flush(spk, txts):
        if not txts:
            return
        para = doc.add_paragraph()
        para.paragraph_format.first_line_indent = Cm(1)
        para.paragraph_format.space_after = Pt(6)
        if spk and spk not in ("UNKNOWN", "-"):
            lb = para.add_run(f"[{spk}] ")
            lb.bold = True
            lb.font.size = Pt(11)
            lb.font.color.rgb = RGBColor(0x2F, 0x54, 0x96)
        ct = para.add_run(" ".join(txts))
        ct.font.size = Pt(12)

    for seg in segments:
        if seg.speaker != current_speaker:
            flush(current_speaker, current_texts)
            current_speaker = seg.speaker
            current_texts   = [seg.text]
        else:
            current_texts.append(seg.text)
    flush(current_speaker, current_texts)

    doc.save(str(out_path))
    logger.info(f"DOCX da luu: {out_path}")
    return out_path


# ── Chunk / Final / Legacy exports ───────────────────────────────────────────

def export_chunk(segments, audio_path, chunk_index, chunk_start_sec, chunk_end_sec,
                 output_dir=None, language="vi", export_srt=False):
    def fmt(s):
        return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"
    suffix      = f"_part{chunk_index:02d}"
    chunk_label = f"Phan {chunk_index} ({fmt(chunk_start_sec)} - {fmt(chunk_end_sec)})"
    merged  = merge_segments(segments)
    results = {"docx": to_docx(merged, audio_path, output_dir, language, suffix, chunk_label)}
    if export_srt:
        results["srt"] = to_srt(merged, audio_path, output_dir, suffix)
    return results


def export_final(all_segments, audio_path, output_dir=None, language="vi", export_srt=False):
    merged  = merge_segments(all_segments)
    results = {"docx": to_docx(merged, audio_path, output_dir, language)}
    if export_srt:
        results["srt"] = to_srt(merged, audio_path, output_dir)
    return results


def export_all(segments, audio_path, output_dir=None, language="vi", export_srt=False):
    return export_final(segments, audio_path, output_dir, language, export_srt)

```

### `pipeline/hardware_detect.py`
```python
"""
pipeline/hardware_detect.py
---------------------------
Auto-detect cấu hình máy và chọn pipeline phù hợp.

3 chế độ:
  BASIC    — CPU only / RAM thấp
  STANDARD — CPU + RAM > 16GB
  FULL     — GPU NVIDIA

Người dùng có thể override thủ công trong GUI.
"""

import os
import platform
import subprocess
from dataclasses import dataclass
from .utils import get_logger

logger = get_logger("hardware")


@dataclass
class HardwareProfile:
    # Thông tin phần cứng
    cpu_cores:    int   = 0
    ram_gb:       float = 0.0
    has_gpu:      bool  = False
    gpu_name:     str   = ""
    gpu_vram_gb:  float = 0.0
    os_name:      str   = ""

    # Chế độ được chọn: "basic" / "standard" / "full"
    mode:         str   = "basic"

    # Engine được chọn
    asr_engine:   str   = "faster-whisper"   # hoặc "whisperx"
    denoise_engine: str = "ffmpeg"            # hoặc "noisereduce"
    diarize:      bool  = False
    compute_type: str   = "int8"
    device:       str   = "cpu"

    # Mô tả ngắn để hiển thị GUI
    @property
    def summary(self) -> str:
        gpu_info = f" | GPU: {self.gpu_name} ({self.gpu_vram_gb:.0f}GB)" if self.has_gpu else ""
        return (
            f"Chế độ: {self.mode.upper()} | "
            f"CPU: {self.cpu_cores} cores | "
            f"RAM: {self.ram_gb:.0f}GB"
            f"{gpu_info}"
        )

    @property
    def mode_label(self) -> str:
        labels = {
            "basic":    "⚡ Basic (CPU)",
            "standard": "🔧 Standard (CPU + RAM lớn)",
            "full":     "🚀 Full (GPU NVIDIA)",
        }
        return labels.get(self.mode, self.mode)

    @property
    def engines_label(self) -> str:
        parts = [self.asr_engine, self.denoise_engine]
        if self.diarize:
            parts.append("pyannote")
        return " + ".join(parts)


def _get_ram_gb() -> float:
    """Lấy tổng RAM (GB)."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass

    # Fallback không cần psutil
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                text=True, timeout=5
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line) / (1024 ** 3)
        elif platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        elif platform.system() == "Darwin":
            out = subprocess.check_output(["sysctl", "hw.memsize"], text=True, timeout=5)
            return int(out.split(":")[1].strip()) / (1024 ** 3)
    except Exception:
        pass

    return 8.0  # fallback


def _get_cpu_cores() -> int:
    """Lấy số CPU cores."""
    try:
        import psutil
        return psutil.cpu_count(logical=False) or os.cpu_count() or 4
    except ImportError:
        return os.cpu_count() or 4


def _detect_nvidia_gpu() -> tuple[bool, str, float]:
    """
    Phát hiện GPU NVIDIA.
    Returns: (has_gpu, gpu_name, vram_gb)
    """
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        )
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        if lines:
            parts    = lines[0].split(",")
            gpu_name = parts[0].strip()
            vram_mb  = float(parts[1].strip()) if len(parts) > 1 else 0
            vram_gb  = vram_mb / 1024
            logger.info(f"Phát hiện GPU: {gpu_name} ({vram_gb:.1f}GB VRAM)")
            return True, gpu_name, vram_gb
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # Thử torch nếu đã cài
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb  = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info(f"Phát hiện GPU (torch): {gpu_name} ({vram_gb:.1f}GB VRAM)")
            return True, gpu_name, vram_gb
    except ImportError:
        pass

    return False, "", 0.0


def _check_noisereduce() -> bool:
    """Kiểm tra noisereduce đã cài chưa."""
    try:
        import noisereduce
        return True
    except ImportError:
        return False


def _check_whisperx() -> bool:
    """Kiểm tra whisperx đã cài chưa."""
    try:
        import whisperx
        return True
    except ImportError:
        return False


def detect() -> HardwareProfile:
    """
    Auto-detect hardware và chọn pipeline tối ưu.
    Returns HardwareProfile với mode và engines đã chọn.
    """
    logger.info("Đang kiểm tra cấu hình phần cứng...")

    ram_gb    = _get_ram_gb()
    cpu_cores = _get_cpu_cores()
    has_gpu, gpu_name, gpu_vram = _detect_nvidia_gpu()
    os_name   = platform.system()

    profile = HardwareProfile(
        cpu_cores   = cpu_cores,
        ram_gb      = ram_gb,
        has_gpu     = has_gpu,
        gpu_name    = gpu_name,
        gpu_vram_gb = gpu_vram,
        os_name     = os_name,
    )

    # ── Chọn chế độ theo hardware ─────────────────────────────────────────
    if has_gpu and gpu_vram >= 4.0:
        # FULL: GPU NVIDIA với đủ VRAM
        profile.mode           = "full"
        profile.device         = "cuda"
        profile.compute_type   = "float16"
        profile.asr_engine     = "whisperx" if _check_whisperx() else "faster-whisper"
        profile.denoise_engine = "noisereduce" if _check_noisereduce() else "ffmpeg"
        profile.diarize        = True

        if profile.asr_engine == "faster-whisper":
            logger.warning(
                "GPU phát hiện nhưng whisperx chưa cài → dùng faster-whisper\n"
                "  Để nâng cấp: pip install whisperx"
            )

    elif ram_gb >= 16:
        # STANDARD: CPU + RAM lớn
        profile.mode           = "standard"
        profile.device         = "cpu"
        profile.compute_type   = "int8"
        profile.asr_engine     = "faster-whisper"
        profile.denoise_engine = "noisereduce" if _check_noisereduce() else "ffmpeg"
        profile.diarize        = False

        if profile.denoise_engine == "ffmpeg":
            logger.info(
                "RAM >= 16GB nhưng noisereduce chưa cài → dùng ffmpeg\n"
                "  Để nâng cấp: pip install noisereduce"
            )

    else:
        # BASIC: CPU thường / RAM thấp
        profile.mode           = "basic"
        profile.device         = "cpu"
        profile.compute_type   = "int8"
        profile.asr_engine     = "faster-whisper"
        profile.denoise_engine = "ffmpeg"
        profile.diarize        = False

    logger.info(
        f"Cấu hình: {profile.mode.upper()} | "
        f"ASR={profile.asr_engine} | "
        f"Denoise={profile.denoise_engine} | "
        f"Diarize={profile.diarize} | "
        f"Device={profile.device}"
    )
    logger.info(f"Hardware: {profile.summary}")

    return profile


def apply_to_env(profile: HardwareProfile):
    """
    Apply profile vào os.environ để các module khác đọc.
    Gọi sau khi detect() hoặc sau khi người dùng override.
    """
    os.environ["WHISPER_DEVICE"]       = profile.device
    os.environ["WHISPER_COMPUTE_TYPE"] = profile.compute_type
    os.environ["HW_MODE"]              = profile.mode
    os.environ["HW_ASR_ENGINE"]        = profile.asr_engine
    os.environ["HW_DENOISE_ENGINE"]    = profile.denoise_engine
    os.environ["HW_DIARIZE"]           = "true" if profile.diarize else "false"

```

### `pipeline/model_locator.py`
```python
"""
pipeline/model_locator.py
-------------------------
Tìm và nhớ vị trí model — hỏi 1 lần, lưu vào models.json, dùng mãi.

Thứ tự tìm:
  1. models.json đã lưu trước → dùng luôn
  2. Quét các thư mục cache phổ biến (Windows/Mac/Linux)
  3. Hỏi người dùng chỉ đường → lưu lại

Không copy, không download lại nếu đã tìm thấy.
"""

import os
import json
import glob
from pathlib import Path
from .utils import get_logger

logger = get_logger("model_locator")

# File lưu path đã tìm được — cạnh project
_BASE        = Path(__file__).parent.parent
_CONFIG_FILE = _BASE / "models.json"

# Các thư mục cache HuggingFace phổ biến
_DEFAULT_SEARCH_PATHS = [
    # Windows
    Path.home() / ".cache" / "huggingface" / "hub",
    Path("C:/Users") / os.getenv("USERNAME", "") / ".cache" / "huggingface" / "hub",
    # Project local
    _BASE / "models" / "hub",
    _BASE / "models",
    # Mac/Linux
    Path.home() / ".cache" / "huggingface" / "hub",
    Path("/usr/local/lib/huggingface"),
]


def _load_config() -> dict:
    """Đọc models.json nếu có."""
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_config(config: dict):
    """Lưu models.json."""
    _CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info(f"Đã lưu config model → {_CONFIG_FILE}")


def _find_in_path(search_root: Path, model_name: str) -> str | None:
    """
    Tìm snapshot dir của model trong search_root.
    Trả về path tuyệt đối đến thư mục chứa model.bin, hoặc None.
    """
    if not search_root.exists():
        return None

    folder_name = f"models--Systran--faster-whisper-{model_name}"
    candidate   = search_root / folder_name

    if not candidate.exists():
        return None

    # Tìm model.bin trong snapshots/
    bins = glob.glob(str(candidate / "**" / "model.bin"), recursive=True)
    if bins:
        snapshot_dir = str(Path(bins[0]).parent)
        logger.info(f"Tìm thấy '{model_name}' tại: {snapshot_dir}")
        return snapshot_dir

    return None


def _scan_all_paths(model_name: str) -> str | None:
    """Quét tất cả thư mục cache phổ biến."""
    seen = set()
    for search_path in _DEFAULT_SEARCH_PATHS:
        sp = str(search_path.resolve()) if search_path.is_absolute() else str(search_path)
        if sp in seen:
            continue
        seen.add(sp)
        result = _find_in_path(Path(search_path), model_name)
        if result:
            return result
    return None


def resolve(
    model_name: str,
    ask_callback=None,   # callback(model_name) → path từ người dùng (GUI/CLI)
) -> str:
    """
    Trả về path tuyệt đối đến snapshot dir của model.
    Nếu không tìm thấy → gọi ask_callback để hỏi người dùng.
    Nếu không có callback → trả về tên model (để faster-whisper tự tìm/download).

    Args:
        model_name:    Tên model: tiny/base/small/medium/large-v2/large-v3
        ask_callback:  Hàm hỏi người dùng, nhận model_name, trả về path string

    Returns:
        Path tuyệt đối đến snapshot dir, hoặc model_name nếu không tìm được
    """
    config = _load_config()

    # 1. Đã lưu trong config trước → kiểm tra còn tồn tại không
    if model_name in config:
        saved_path = config[model_name]
        if Path(saved_path).exists():
            logger.info(f"Dùng path đã lưu: {saved_path}")
            return saved_path
        else:
            logger.warning(f"Path đã lưu không còn tồn tại: {saved_path} → tìm lại")
            del config[model_name]
            _save_config(config)

    # 2. Quét tự động
    logger.info(f"Tìm model '{model_name}' trong cache hệ thống...")
    found = _scan_all_paths(model_name)
    if found:
        config[model_name] = found
        _save_config(config)
        return found

    # 3. Hỏi người dùng
    if ask_callback:
        logger.info(f"Không tìm thấy '{model_name}' tự động → hỏi người dùng")
        user_path = ask_callback(model_name)
        if user_path:
            # Validate path có model.bin không
            bins = glob.glob(str(Path(user_path) / "**" / "model.bin"), recursive=True)
            if not bins:
                # Có thể user chỉ vào thư mục hub, không vào snapshot — tìm sâu hơn
                folder_name = f"models--Systran--faster-whisper-{model_name}"
                deep_bins   = glob.glob(
                    str(Path(user_path) / "**" / folder_name / "**" / "model.bin"),
                    recursive=True
                )
                if deep_bins:
                    user_path = str(Path(deep_bins[0]).parent)
                    bins      = [deep_bins[0]]

            if bins:
                snapshot_dir = str(Path(bins[0]).parent)
                config[model_name] = snapshot_dir
                _save_config(config)
                logger.info(f"Đã lưu path người dùng cung cấp: {snapshot_dir}")
                return snapshot_dir
            else:
                logger.warning(f"Không tìm thấy model.bin trong: {user_path}")

    # 4. Fallback — để faster-whisper tự xử lý (sẽ download nếu cần)
    logger.warning(
        f"Không tìm thấy '{model_name}' ở bất kỳ đâu.\n"
        f"  Sẽ download vào: {_BASE / 'models' / 'hub'}\n"
        f"  Hoặc anh có thể chỉ đường thủ công trong GUI."
    )
    return model_name


def scan_available() -> dict:
    """
    Quét và trả về tất cả model có sẵn trên máy.
    Returns: {model_name: snapshot_path}
    """
    available = {}
    models    = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

    config = _load_config()

    for m in models:
        # Ưu tiên config đã lưu
        if m in config and Path(config[m]).exists():
            available[m] = config[m]
            continue
        # Quét tự động
        found = _scan_all_paths(m)
        if found:
            available[m] = found
            config[m]    = found

    if available:
        _save_config(config)

    return available


def clear_cache():
    """Xóa models.json để tìm lại từ đầu."""
    if _CONFIG_FILE.exists():
        _CONFIG_FILE.unlink()
        logger.info("Đã xóa models.json — sẽ tìm lại lần chạy sau")

```

### `pipeline/postprocess.py`
```python
"""
pipeline/postprocess.py
-----------------------
Dùng LLM offline (Ollama) để sửa lỗi text sau khi Whisper transcribe xong.

3 tầng cải tiến:
  Tầng 2 — Prompt động: build từ domain + glossary trong .env
  Tầng 3 — Confidence: ưu tiên sửa segment Whisper không chắc
"""

import json
import os
import urllib.request
import urllib.error
from .transcribe import Segment
from .utils import get_logger

logger = get_logger("postprocess")

OLLAMA_URL    = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:3b"

# Ngưỡng confidence — segment dưới mức này được đánh dấu [?] để LLM ưu tiên
CONF_THRESHOLD = float(os.getenv("LLM_CONF_THRESHOLD", "0.6"))


def _build_prompt(domain_hint: str, glossary: dict) -> str:
    """
    Build prompt động từ domain + glossary.
    Không hardcode ví dụ — tự sinh từ context thực tế.
    """
    # Phần cố định — luôn có
    base = """Bạn là công cụ sửa lỗi transcript tiếng Việt từ phần mềm nhận dạng giọng nói (STT).
STT hay nhầm các từ nghe gần giống nhau, ví dụ phổ biến:
  "ghi ấm" → "ghi âm"     "ấm" → "ôm"      "quái" → "quay"
  "bà con" → "và con"     "đô" → "độ"       "trên đấy" → "trên đây"

Nhiệm vụ: Nhận danh sách dòng [0], [1], [2]... và sửa lỗi STT, trả về đúng format đó.

Quy tắc BẮT BUỘC:
1. GIỮ NGUYÊN format [số] ở đầu mỗi dòng
2. Dòng có [?] ở cuối = Whisper không chắc → ưu tiên sửa cẩn thận hơn
3. Chỉ sửa từ bị nhận sai âm thanh — KHÔNG thêm/bớt nội dung
4. Nếu dòng đã đúng → giữ nguyên, vẫn phải in ra (bỏ dấu [?] nếu có)
5. Trả về CHỈ danh sách [số] text — không giải thích, không markdown"""

    # Thêm domain context nếu có
    if domain_hint:
        base += f"\n\nNgữ cảnh: đây là transcript thuộc lĩnh vực '{domain_hint}'."
        base += "\nHãy ưu tiên các thuật ngữ chuyên ngành đúng với lĩnh vực này."

    # Thêm glossary nếu có — đây là phần quan trọng nhất cho cuộc họp
    if glossary:
        base += "\n\nTừ điển thuật ngữ (STT hay nhầm → từ đúng):"
        for wrong, correct in glossary.items():
            base += f"\n  \"{wrong}\" → \"{correct}\""

    # Ví dụ input/output
    base += """

Ví dụ input:
[0] Bố ghi ấm nè quái ghi ấm [?]
[1] Mẹ nấu món ngon rất tuyệt

Ví dụ output đúng:
[0] Bố ghi âm nè quay ghi âm
[1] Mẹ nấu món ngon rất tuyệt"""

    return base


def _parse_glossary() -> dict:
    """
    Đọc glossary từ env LLM_GLOSSARY.
    Format: "sai1,đúng1;sai2,đúng2"
    Ví dụ: "TMDT,TMĐT;bql,Ban Quản Lý;hợp đồng,hợp đồng"
    """
    raw = os.getenv("LLM_GLOSSARY", "").strip()
    if not raw:
        return {}
    result = {}
    for pair in raw.split(";"):
        pair = pair.strip()
        if "," in pair:
            parts = pair.split(",", 1)
            wrong, correct = parts[0].strip(), parts[1].strip()
            if wrong and correct:
                result[wrong] = correct
    if result:
        logger.info(f"Glossary: {len(result)} từ — {list(result.items())[:3]}...")
    return result


def _call_ollama(text: str, model: str, prompt: str) -> str | None:
    payload = json.dumps({
        "model":  model,
        "prompt": f"{prompt}\n\nInput:\n{text}\n\nOutput:",
        "stream": False,
        "options": {
            "temperature":  0.05,
            "num_predict":  len(text) * 2 + 300,
            "stop":         [],
        }
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt, timeout_sec in enumerate([120, 180], start=1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                result   = json.loads(resp.read())
                response = result.get("response", "").strip()
                dur      = result.get("total_duration", 0) / 1e9
                logger.debug(f"Ollama {dur:.1f}s: {response[:100]}")
                return response

        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:300]
            logger.error(f"Ollama HTTP {e.code}: {body}")
            logger.error(f"Gợi ý: ollama pull {model}")
            return None

        except urllib.error.URLError as e:
            reason = str(e.reason)
            if "refused" in reason.lower():
                logger.error("Ollama không chạy")
                return None
            if attempt < 2:
                logger.warning(f"Timeout lần {attempt} ({timeout_sec}s) — thử lại...")
            else:
                logger.warning(f"Timeout sau {timeout_sec}s — bỏ qua")
                return None

        except Exception as e:
            logger.warning(f"Ollama lỗi: {type(e).__name__}: {e}")
            return None
    return None


def _check_ollama(model: str) -> bool:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data      = json.loads(resp.read())
            models    = [m["name"] for m in data.get("models", [])]
            available = any(m.startswith(model.split(":")[0]) for m in models)
            if not available:
                logger.warning(
                    f"Model '{model}' chưa có. Chạy: ollama pull {model}\n"
                    f"Các model hiện có: {', '.join(models) or 'không có'}"
                )
            return available
    except Exception:
        return False


def _parse_response(corrected: str, batch_size: int) -> dict:
    """Parse output LLM dạng [0] text, robust với format lệch."""
    lines = {}
    for line in corrected.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            try:
                idx  = int(line[1: line.index("]")])
                text = line[line.index("]") + 1:].strip()
                # Bỏ dấu [?] nếu LLM để lại
                text = text.replace("[?]", "").strip()
                if text and 0 <= idx < batch_size:
                    lines[idx] = text
            except ValueError:
                pass

    # Fallback: ghép theo thứ tự dòng
    if not lines:
        raw_lines = [l.strip() for l in corrected.splitlines() if l.strip()]
        for i, text in enumerate(raw_lines[:batch_size]):
            lines[i] = text.replace("[?]", "").strip()

    return lines


def run(
    segments:    list[Segment],
    enabled:     bool  = True,
    model:       str   = None,
    domain_hint: str   = "",
    batch_size:  int   = 5,
) -> list[Segment]:

    if not enabled:
        logger.info("LLM post-process tắt — bỏ qua")
        return segments

    if not segments:
        return segments

    model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

    logger.info(f"Kiểm tra Ollama ({model})…")
    if not _check_ollama(model):
        logger.warning(f"Ollama không sẵn sàng → bỏ qua. Chạy: ollama pull {model}")
        return segments

    # Build prompt động
    domain_hint = domain_hint or os.getenv("LLM_DOMAIN", "")
    glossary    = _parse_glossary()
    prompt      = _build_prompt(domain_hint, glossary)

    # Log thống kê confidence
    low_conf = [s for s in segments if s.confidence < CONF_THRESHOLD]
    logger.info(
        f"LLM post-process: {len(segments)} segment "
        f"({len(low_conf)} thấp tin cậy cần ưu tiên sửa), "
        f"model={model}, batch={batch_size}"
    )
    if domain_hint:
        logger.info(f"Domain: {domain_hint}")
    if glossary:
        logger.info(f"Glossary: {len(glossary)} từ")

    result_segments = list(segments)
    total_fixed     = 0

    for batch_start in range(0, len(result_segments), batch_size):
        batch = result_segments[batch_start: batch_start + batch_size]

        # Đánh dấu [?] vào segment thấp confidence để LLM ưu tiên
        numbered_lines = []
        for i, seg in enumerate(batch):
            marker = " [?]" if seg.confidence < CONF_THRESHOLD else ""
            numbered_lines.append(f"[{i}] {seg.text}{marker}")
        numbered = "\n".join(numbered_lines)

        logger.debug(f"Batch input:\n{numbered}")
        corrected = _call_ollama(numbered, model, prompt)

        if not corrected:
            logger.warning(f"Batch {batch_start//batch_size + 1}: LLM không trả về — giữ nguyên")
            continue

        logger.debug(f"Batch output:\n{corrected}")
        lines       = _parse_response(corrected, len(batch))
        fixed_count = 0

        for i, seg in enumerate(batch):
            if i in lines and lines[i]:
                original = seg.text
                seg.text = lines[i]
                if original != seg.text:
                    fixed_count += 1
                    total_fixed += 1
                    conf_tag = f" [conf={seg.confidence:.2f}]" if seg.confidence < CONF_THRESHOLD else ""
                    logger.info(f"  [{i}]{conf_tag} {original!r} → {seg.text!r}")

        logger.info(
            f"Batch {batch_start//batch_size + 1}/{(len(result_segments)-1)//batch_size + 1}: "
            f"sửa {fixed_count}/{len(batch)} segment"
        )

    logger.info(f"LLM post-process hoàn tất — tổng sửa {total_fixed}/{len(segments)} segment")
    return result_segments

```

### `pipeline/transcribe.py`
```python
"""
pipeline/transcribe.py
----------------------
Wrapper faster-whisper.
Trả về list[Segment] — mỗi segment có start, end, text, words, confidence.

Model được load 1 lần duy nhất và cache lại — các chunk sau dùng lại.

Tầng 1 fix: VAD parameters tunable — giảm ngưỡng để bỏ sót ít hơn.
Tầng 3 fix: Ghi confidence vào segment để LLM ưu tiên sửa đoạn kém chắc.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .utils import get_logger

logger = get_logger("transcribe")

# ── Model cache — load 1 lần, dùng mãi trong session ─────────────────────────
_model_cache: dict = {}


@dataclass
class Segment:
    start:      float
    end:        float
    text:       str
    speaker:    Optional[str]   = None
    words:      list            = field(default_factory=list)
    confidence: float           = 1.0   # avg log_prob → 0.0=tệ, 1.0=tốt
    no_speech:  float           = 0.0   # xác suất không có giọng nói


def get_model(model_name: str, device: str, compute_type: str, ask_callback=None):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper chưa được cài. Chạy install.bat trước.")

    cache_key = f"{model_name}__{device}__{compute_type}"
    if cache_key not in _model_cache:
        logger.info(f"Load model '{model_name}' ({device}/{compute_type}) — lần đầu, cache lại...")

        # Dùng model_locator để tìm path — không copy, không download lại
        from .model_locator import resolve
        model_path = resolve(model_name, ask_callback=ask_callback)

        _model_cache[cache_key] = WhisperModel(
            model_path,
            device=device,
            compute_type=compute_type,
        )
        logger.info(f"Model '{model_name}' sẵn sàng.")
    else:
        logger.info(f"Dùng lại model '{model_name}' từ cache (không load lại).")
    return _model_cache[cache_key]


def run(
    audio_path:       str | Path,
    model_name:       str   = "medium",
    language:         str   = "vi",
    device:           str   = "cpu",
    compute_type:     str   = "int8",
    beam_size:        int   = 5,
    vad_filter:       bool  = True,
    word_timestamps:  bool  = False,
    ask_callback             = None,
    # ── VAD parameters ────────────────────────────────────────────────────
    vad_threshold:          float = 0.3,
    vad_min_silence_ms:     int   = 300,
    vad_speech_pad_ms:      int   = 400,
    # ── Anti-hallucination (từ whisper_watcher v5) ────────────────────────
    # QUAN TRỌNG NHẤT: tắt để không bị lặp/hallucination với file dài
    condition_on_previous_text: bool  = False,
    # Lọc segment bị nén quá mức — thường là hallucination
    compression_ratio_threshold: float = 2.4,
    # Lọc segment xác suất thấp
    log_prob_threshold:         float = -1.0,
    # Ngưỡng phát hiện im lặng
    no_speech_threshold:        float = 0.6,
    # Phạt nếu lặp lại
    repetition_penalty:         float = 1.2,
) -> list[Segment]:
    """
    Chạy faster-whisper trên audio_path.
    Trả về list[Segment] với confidence score.

    Anti-hallucination params từ whisper_watcher v5:
    - condition_on_previous_text=False  → không bị lặp với file dài
    - compression_ratio_threshold=2.4   → lọc hallucination
    - repetition_penalty=1.2            → chống lặp từ/câu
    """
    path  = Path(audio_path)
    model = get_model(model_name, device, compute_type, ask_callback=ask_callback)

    logger.info(f"Bắt đầu transcribe: {path.name}  lang={language}  vad={vad_filter}")
    logger.info(
        f"Anti-hallucination: condition_on_prev={condition_on_previous_text}  "
        f"compression_ratio={compression_ratio_threshold}  "
        f"repetition_penalty={repetition_penalty}"
    )
    if vad_filter:
        logger.info(
            f"VAD: threshold={vad_threshold}  "
            f"min_silence={vad_min_silence_ms}ms  "
            f"speech_pad={vad_speech_pad_ms}ms"
        )

    vad_params = {
        "threshold":               vad_threshold,
        "min_silence_duration_ms": vad_min_silence_ms,
        "speech_pad_ms":           vad_speech_pad_ms,
    } if vad_filter else {}

    raw_segments, info = model.transcribe(
        str(path),
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters=vad_params if vad_filter else None,
        word_timestamps=word_timestamps,
        # ── Anti-hallucination ─────────────────────────────────────────
        condition_on_previous_text  = condition_on_previous_text,
        compression_ratio_threshold = compression_ratio_threshold,
        log_prob_threshold          = log_prob_threshold,
        no_speech_threshold         = no_speech_threshold,
        repetition_penalty          = repetition_penalty,
    )

    logger.info(
        f"Detected language: {info.language}  "
        f"probability: {info.language_probability:.2f}"
    )

    segments: list[Segment] = []
    low_conf_count = 0
    prev_text      = ""   # Dedup — bỏ segment trùng với segment trước

    for seg in raw_segments:
        text = seg.text.strip()
        if not text:
            continue

        # Bỏ qua nếu trùng segment trước (từ whisper_watcher v5)
        if text == prev_text:
            logger.debug(f"  [DEDUP] Bỏ segment trùng: {text[:40]}")
            continue
        prev_text = text

        words = []
        if word_timestamps and hasattr(seg, "words") and seg.words:
            words = [{"word": w.word, "start": w.start, "end": w.end}
                     for w in seg.words]

        # Confidence: avg_logprob là âm, -0.2 ~ tốt, -0.8 ~ kém
        # Chuẩn hóa về [0,1]: 0=tệ, 1=tốt
        raw_conf  = getattr(seg, "avg_logprob",    -0.5)
        no_speech = getattr(seg, "no_speech_prob",  0.0)
        conf      = max(0.0, min(1.0, 1.0 + raw_conf / 1.0))

        if conf < 0.5 or no_speech > 0.3:
            low_conf_count += 1
            logger.debug(
                f"  [!] Thấp tin cậy [{seg.start:.1f}s]: "
                f"conf={conf:.2f} no_speech={no_speech:.2f} | {text[:50]}"
            )
        else:
            logger.debug(f"  [{seg.start:.2f}s → {seg.end:.2f}s] conf={conf:.2f} | {text[:60]}")

        segments.append(Segment(
            start=seg.start, end=seg.end, text=text,
            words=words, confidence=conf, no_speech=no_speech,
        ))

    logger.info(f"Xong: {len(segments)} segment  ({low_conf_count} segment thấp tin cậy)")
    return segments

```

### `pipeline/utils.py`
```python
"""
pipeline/utils.py
-----------------
Các hàm tiện ích dùng chung trong pipeline.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# ── Logging ──────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s  %(name)s: %(message)s",
                                datefmt="%H:%M:%S")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ── File helpers ──────────────────────────────────────────────────────────────

AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".mkv"}

def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS

def stem(path: Path) -> str:
    """Tên file không có extension."""
    return Path(path).stem

def resolve_output_dir(audio_path: Path, override: str | None = None) -> Path:
    """
    Trả về thư mục output.
    - Nếu override được set (từ .env OUTPUT_DIR) → dùng override
    - Nếu không → cùng thư mục với file audio
    """
    if override:
        out = Path(override)
        out.mkdir(parents=True, exist_ok=True)
        return out
    return Path(audio_path).parent

def timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Segment helpers ───────────────────────────────────────────────────────────

def seconds_to_srt_time(seconds: float) -> str:
    """Chuyển float seconds → định dạng SRT: HH:MM:SS,mmm"""
    millis = int(round(seconds * 1000))
    h  = millis // 3_600_000; millis %= 3_600_000
    m  = millis //    60_000; millis %=    60_000
    s  = millis //     1_000; millis %=     1_000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"

```


## 6. The code_dependency graph (only Method B uses this)

Trích bằng AST từ codebase Mục 4. Mỗi cạnh có `evidence` = file:line.

```json
{
 "schema": {
  "node_types": [
   "Module",
   "Function",
   "ConfigVar",
   "Model"
  ],
  "edge_types": [
   "imports",
   "calls",
   "reads-env",
   "resolves"
  ]
 },
 "nodes": [
  {
   "id": "mod:audio",
   "type": "Module",
   "label": "audio",
   "file": "audio.py"
  },
  {
   "id": "mod:utils",
   "type": "Module",
   "label": "utils"
  },
  {
   "id": "mod:denoise",
   "type": "Module",
   "label": "denoise",
   "file": "denoise.py"
  },
  {
   "id": "env:HW_DENOISE_ENGINE",
   "type": "ConfigVar",
   "label": "HW_DENOISE_ENGINE"
  },
  {
   "id": "mod:diarize",
   "type": "Module",
   "label": "diarize",
   "file": "diarize.py"
  },
  {
   "id": "mod:transcribe",
   "type": "Module",
   "label": "transcribe"
  },
  {
   "id": "env:HF_TOKEN",
   "type": "ConfigVar",
   "label": "HF_TOKEN"
  },
  {
   "id": "mod:export",
   "type": "Module",
   "label": "export",
   "file": "export.py"
  },
  {
   "id": "mod:hardware_detect",
   "type": "Module",
   "label": "hardware_detect",
   "file": "hardware_detect.py"
  },
  {
   "id": "mod:model_locator",
   "type": "Module",
   "label": "model_locator",
   "file": "model_locator.py"
  },
  {
   "id": "model:whisper",
   "type": "Model",
   "label": "whisper model"
  },
  {
   "id": "env:USERNAME",
   "type": "ConfigVar",
   "label": "USERNAME"
  },
  {
   "id": "mod:postprocess",
   "type": "Module",
   "label": "postprocess",
   "file": "postprocess.py"
  },
  {
   "id": "env:LLM_CONF_THRESHOLD",
   "type": "ConfigVar",
   "label": "LLM_CONF_THRESHOLD"
  },
  {
   "id": "env:OLLAMA_MODEL",
   "type": "ConfigVar",
   "label": "OLLAMA_MODEL"
  },
  {
   "id": "env:LLM_DOMAIN",
   "type": "ConfigVar",
   "label": "LLM_DOMAIN"
  },
  {
   "id": "env:LLM_GLOSSARY",
   "type": "ConfigVar",
   "label": "LLM_GLOSSARY"
  },
  {
   "id": "mod:main",
   "type": "Module",
   "label": "main",
   "file": "main.py"
  },
  {
   "id": "env:WHISPER_MODEL",
   "type": "ConfigVar",
   "label": "WHISPER_MODEL"
  },
  {
   "id": "env:WHISPER_LANGUAGE",
   "type": "ConfigVar",
   "label": "WHISPER_LANGUAGE"
  },
  {
   "id": "env:WHISPER_DEVICE",
   "type": "ConfigVar",
   "label": "WHISPER_DEVICE"
  },
  {
   "id": "env:WHISPER_COMPUTE_TYPE",
   "type": "ConfigVar",
   "label": "WHISPER_COMPUTE_TYPE"
  },
  {
   "id": "env:OUTPUT_DIR",
   "type": "ConfigVar",
   "label": "OUTPUT_DIR"
  },
  {
   "id": "env:DENOISE_LEVEL",
   "type": "ConfigVar",
   "label": "DENOISE_LEVEL"
  },
  {
   "id": "env:SILENCE_THRESHOLD_DB",
   "type": "ConfigVar",
   "label": "SILENCE_THRESHOLD_DB"
  },
  {
   "id": "env:SILENCE_MIN_SEC",
   "type": "ConfigVar",
   "label": "SILENCE_MIN_SEC"
  },
  {
   "id": "env:VAD_THRESHOLD",
   "type": "ConfigVar",
   "label": "VAD_THRESHOLD"
  },
  {
   "id": "env:VAD_MIN_SILENCE_MS",
   "type": "ConfigVar",
   "label": "VAD_MIN_SILENCE_MS"
  },
  {
   "id": "env:VAD_SPEECH_PAD_MS",
   "type": "ConfigVar",
   "label": "VAD_SPEECH_PAD_MS"
  },
  {
   "id": "env:COMPRESSION_RATIO_THRESHOLD",
   "type": "ConfigVar",
   "label": "COMPRESSION_RATIO_THRESHOLD"
  },
  {
   "id": "env:LOG_PROB_THRESHOLD",
   "type": "ConfigVar",
   "label": "LOG_PROB_THRESHOLD"
  },
  {
   "id": "env:NO_SPEECH_THRESHOLD",
   "type": "ConfigVar",
   "label": "NO_SPEECH_THRESHOLD"
  },
  {
   "id": "env:REPETITION_PENALTY",
   "type": "ConfigVar",
   "label": "REPETITION_PENALTY"
  },
  {
   "id": "env:DENOISE_ENABLED",
   "type": "ConfigVar",
   "label": "DENOISE_ENABLED"
  },
  {
   "id": "env:LLM_ENABLED",
   "type": "ConfigVar",
   "label": "LLM_ENABLED"
  },
  {
   "id": "env:CONDITION_ON_PREVIOUS_TEXT",
   "type": "ConfigVar",
   "label": "CONDITION_ON_PREVIOUS_TEXT"
  }
 ],
 "edges": [
  {
   "source": "mod:audio",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "audio.py:15"
  },
  {
   "source": "mod:denoise",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "denoise.py:19"
  },
  {
   "source": "mod:denoise",
   "target": "env:HW_DENOISE_ENGINE",
   "type": "reads-env",
   "evidence": "denoise.py:100"
  },
  {
   "source": "mod:diarize",
   "target": "mod:transcribe",
   "type": "imports",
   "evidence": "diarize.py:18"
  },
  {
   "source": "mod:diarize",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "diarize.py:19"
  },
  {
   "source": "mod:diarize",
   "target": "mod:audio",
   "type": "imports",
   "evidence": "diarize.py:92"
  },
  {
   "source": "mod:diarize",
   "target": "env:HF_TOKEN",
   "type": "reads-env",
   "evidence": "diarize.py:89"
  },
  {
   "source": "mod:export",
   "target": "mod:transcribe",
   "type": "imports",
   "evidence": "export.py:13"
  },
  {
   "source": "mod:export",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "export.py:14"
  },
  {
   "source": "mod:hardware_detect",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "hardware_detect.py:18"
  },
  {
   "source": "mod:model_locator",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "model_locator.py:18"
  },
  {
   "source": "mod:model_locator",
   "target": "model:whisper",
   "type": "resolves",
   "evidence": "model_locator.py:87"
  },
  {
   "source": "mod:model_locator",
   "target": "env:USERNAME",
   "type": "reads-env",
   "evidence": "model_locator.py:30"
  },
  {
   "source": "mod:postprocess",
   "target": "mod:transcribe",
   "type": "imports",
   "evidence": "postprocess.py:15"
  },
  {
   "source": "mod:postprocess",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "postprocess.py:16"
  },
  {
   "source": "mod:postprocess",
   "target": "env:LLM_CONF_THRESHOLD",
   "type": "reads-env",
   "evidence": "postprocess.py:24"
  },
  {
   "source": "mod:postprocess",
   "target": "env:OLLAMA_MODEL",
   "type": "reads-env",
   "evidence": "postprocess.py:204"
  },
  {
   "source": "mod:postprocess",
   "target": "env:LLM_DOMAIN",
   "type": "reads-env",
   "evidence": "postprocess.py:212"
  },
  {
   "source": "mod:postprocess",
   "target": "env:LLM_GLOSSARY",
   "type": "reads-env",
   "evidence": "postprocess.py:78"
  },
  {
   "source": "mod:transcribe",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "transcribe.py:18"
  },
  {
   "source": "mod:transcribe",
   "target": "mod:model_locator",
   "type": "imports",
   "evidence": "transcribe.py:48"
  },
  {
   "source": "mod:transcribe",
   "target": "model:whisper",
   "type": "resolves",
   "evidence": "transcribe.py:49"
  },
  {
   "source": "mod:main",
   "target": "env:WHISPER_MODEL",
   "type": "reads-env",
   "evidence": "main.py:101"
  },
  {
   "source": "mod:main",
   "target": "env:WHISPER_LANGUAGE",
   "type": "reads-env",
   "evidence": "main.py:102"
  },
  {
   "source": "mod:main",
   "target": "env:WHISPER_DEVICE",
   "type": "reads-env",
   "evidence": "main.py:103"
  },
  {
   "source": "mod:main",
   "target": "env:WHISPER_COMPUTE_TYPE",
   "type": "reads-env",
   "evidence": "main.py:104"
  },
  {
   "source": "mod:main",
   "target": "env:OUTPUT_DIR",
   "type": "reads-env",
   "evidence": "main.py:105"
  },
  {
   "source": "mod:main",
   "target": "env:OLLAMA_MODEL",
   "type": "reads-env",
   "evidence": "main.py:114"
  },
  {
   "source": "mod:main",
   "target": "env:LLM_DOMAIN",
   "type": "reads-env",
   "evidence": "main.py:115"
  },
  {
   "source": "mod:main",
   "target": "mod:audio",
   "type": "imports",
   "evidence": "main.py:264"
  },
  {
   "source": "mod:main",
   "target": "mod:transcribe",
   "type": "imports",
   "evidence": "main.py:265"
  },
  {
   "source": "mod:main",
   "target": "mod:diarize",
   "type": "imports",
   "evidence": "main.py:266"
  },
  {
   "source": "mod:main",
   "target": "mod:export",
   "type": "imports",
   "evidence": "main.py:267"
  },
  {
   "source": "mod:main",
   "target": "mod:denoise",
   "type": "imports",
   "evidence": "main.py:268"
  },
  {
   "source": "mod:main",
   "target": "mod:postprocess",
   "type": "imports",
   "evidence": "main.py:269"
  },
  {
   "source": "mod:main",
   "target": "mod:model_locator",
   "type": "imports",
   "evidence": "main.py:57"
  },
  {
   "source": "mod:main",
   "target": "mod:hardware_detect",
   "type": "imports",
   "evidence": "main.py:71"
  },
  {
   "source": "mod:main",
   "target": "env:DENOISE_LEVEL",
   "type": "reads-env",
   "evidence": "main.py:112"
  },
  {
   "source": "mod:main",
   "target": "env:SILENCE_THRESHOLD_DB",
   "type": "reads-env",
   "evidence": "main.py:116"
  },
  {
   "source": "mod:main",
   "target": "env:SILENCE_MIN_SEC",
   "type": "reads-env",
   "evidence": "main.py:117"
  },
  {
   "source": "mod:main",
   "target": "env:VAD_THRESHOLD",
   "type": "reads-env",
   "evidence": "main.py:119"
  },
  {
   "source": "mod:main",
   "target": "env:VAD_MIN_SILENCE_MS",
   "type": "reads-env",
   "evidence": "main.py:120"
  },
  {
   "source": "mod:main",
   "target": "env:VAD_SPEECH_PAD_MS",
   "type": "reads-env",
   "evidence": "main.py:121"
  },
  {
   "source": "mod:main",
   "target": "env:COMPRESSION_RATIO_THRESHOLD",
   "type": "reads-env",
   "evidence": "main.py:125"
  },
  {
   "source": "mod:main",
   "target": "env:LOG_PROB_THRESHOLD",
   "type": "reads-env",
   "evidence": "main.py:126"
  },
  {
   "source": "mod:main",
   "target": "env:NO_SPEECH_THRESHOLD",
   "type": "reads-env",
   "evidence": "main.py:127"
  },
  {
   "source": "mod:main",
   "target": "env:REPETITION_PENALTY",
   "type": "reads-env",
   "evidence": "main.py:128"
  },
  {
   "source": "mod:main",
   "target": "env:HW_DENOISE_ENGINE",
   "type": "reads-env",
   "evidence": "main.py:281"
  },
  {
   "source": "mod:main",
   "target": "mod:utils",
   "type": "imports",
   "evidence": "main.py:444"
  },
  {
   "source": "mod:main",
   "target": "env:DENOISE_ENABLED",
   "type": "reads-env",
   "evidence": "main.py:111"
  },
  {
   "source": "mod:main",
   "target": "env:LLM_ENABLED",
   "type": "reads-env",
   "evidence": "main.py:113"
  },
  {
   "source": "mod:main",
   "target": "env:CONDITION_ON_PREVIOUS_TEXT",
   "type": "reads-env",
   "evidence": "main.py:124"
  },
  {
   "source": "mod:audio",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "audio.py:17",
   "via": "get_logger"
  },
  {
   "source": "mod:audio",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "audio.py:43",
   "via": "is_audio_file"
  },
  {
   "source": "mod:denoise",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "denoise.py:21",
   "via": "get_logger"
  },
  {
   "source": "mod:diarize",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "diarize.py:21",
   "via": "get_logger"
  },
  {
   "source": "mod:export",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "export.py:16",
   "via": "get_logger"
  },
  {
   "source": "mod:export",
   "target": "mod:transcribe",
   "type": "calls",
   "evidence": "export.py:32",
   "via": "Seg"
  },
  {
   "source": "mod:export",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "export.py:116",
   "via": "stem"
  },
  {
   "source": "mod:export",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "export.py:164",
   "via": "seconds_to_srt_time"
  },
  {
   "source": "mod:hardware_detect",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "hardware_detect.py:20",
   "via": "get_logger"
  },
  {
   "source": "mod:model_locator",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "model_locator.py:20",
   "via": "get_logger"
  },
  {
   "source": "mod:postprocess",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "postprocess.py:18",
   "via": "get_logger"
  },
  {
   "source": "mod:transcribe",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "transcribe.py:20",
   "via": "get_logger"
  },
  {
   "source": "mod:transcribe",
   "target": "mod:model_locator",
   "type": "calls",
   "evidence": "transcribe.py:49",
   "via": "resolve"
  },
  {
   "source": "mod:main",
   "target": "mod:audio",
   "type": "calls",
   "evidence": "main.py:271",
   "via": "inspect"
  },
  {
   "source": "mod:main",
   "target": "mod:model_locator",
   "type": "calls",
   "evidence": "main.py:58",
   "via": "scan_available"
  },
  {
   "source": "mod:main",
   "target": "mod:hardware_detect",
   "type": "calls",
   "evidence": "main.py:72",
   "via": "detect"
  },
  {
   "source": "mod:main",
   "target": "mod:hardware_detect",
   "type": "calls",
   "evidence": "main.py:73",
   "via": "apply_to_env"
  },
  {
   "source": "mod:main",
   "target": "mod:denoise",
   "type": "calls",
   "evidence": "main.py:282",
   "via": "denoise"
  },
  {
   "source": "mod:main",
   "target": "mod:transcribe",
   "type": "calls",
   "evidence": "main.py:384",
   "via": "transcribe"
  },
  {
   "source": "mod:main",
   "target": "mod:postprocess",
   "type": "calls",
   "evidence": "main.py:405",
   "via": "postprocess"
  },
  {
   "source": "mod:main",
   "target": "mod:diarize",
   "type": "calls",
   "evidence": "main.py:412",
   "via": "do_diarize"
  },
  {
   "source": "mod:main",
   "target": "mod:export",
   "type": "calls",
   "evidence": "main.py:413",
   "via": "export_all"
  },
  {
   "source": "mod:main",
   "target": "mod:hardware_detect",
   "type": "calls",
   "evidence": "main.py:698",
   "via": "HardwareProfile"
  },
  {
   "source": "mod:main",
   "target": "mod:export",
   "type": "calls",
   "evidence": "main.py:364",
   "via": "export_final"
  },
  {
   "source": "mod:main",
   "target": "mod:utils",
   "type": "calls",
   "evidence": "main.py:452",
   "via": "is_audio_file"
  },
  {
   "source": "mod:main",
   "target": "mod:export",
   "type": "calls",
   "evidence": "main.py:344",
   "via": "export_chunk"
  }
 ]
}
```



## 7. Result format (return ONLY this table)

Token-counting convention (same as Rounds 1 and 2):
- Split text into units: each cluster matching `[A-Za-z0-9_]+`, or a single non-whitespace/non-alphanumeric character.
- Each unit counts as `1 + floor((length-1)/6)` tokens.
- **token_in at each turn** = all tokens loaded for that turn (accumulated history for A; accumulated signatures for B).
- token_out = tokens of the answer generated at that turn.

```
AI: <your AI name>

Per-turn breakdown:
Turn | A.token_in | A.token_out | B.token_in | B.token_out
  1  |            |             |            |
  2  |            |             |            |
  3  |            |             |            |
  4  |            |             |            |
TOTAL|            |             |            |

Growth ratio (B.token_in / A.token_in):
  Turn 1: ___   Turn 2: ___   Turn 3: ___   Turn 4: ___

Does B.token_in grow slower than A.token_in across turns? (yes / no / inconclusive): ___

Answer quality check — did both methods reach the same answer for each turn?
  Q1 match: yes/no   Q2 match: yes/no   Q3 match: yes/no   Q4 match: yes/no
```

After the table, write exactly 1 line: note any turn where the two methods gave materially different answers, and why. If all matched, write "All matched."

---

## Notes on experimental validity

- **Self-reported measurement:** you count your own tokens using the convention above. Trust ratios, not absolute numbers.
- **Graph signature quality matters:** if your Turn 1 signature misses key nodes, Method B may degrade at later turns. Record this if it happens — it is a valid finding.
- **Answer quality is a secondary check:** the primary metric is token_in growth curve. If a method produces a wrong or degraded answer, note it.
- **Do not speculate.** If a question has no data in the codebase, answer "not found" under both methods.
