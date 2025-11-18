import os
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# =========================
#  YT Downloader Pro Max
#  GUI Edition (Windows)
#  Author: @shoxrux.edit
# =========================

# ---------- SETTINGS ----------

def get_default_download_dir():
    home = os.path.expanduser("~")
    return os.path.join(home, "YouTubeDownloads")

DOWNLOAD_DIR = get_default_download_dir()
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ---------- CORE LOGIC ----------

def run_command(cmd):
    """Run external command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError as e:
        return "", str(e), 1
    except Exception as e:
        return "", str(e), 1


def find_last_downloaded_file(directory):
    """Return most recently modified .mp4/.webm/.m4a/.mp3 file."""
    exts = (".webm", ".mp4", ".m4a", ".mp3")
    candidates = []
    for name in os.listdir(directory):
        if name.lower().endswith(exts):
            full = os.path.join(directory, name)
            candidates.append((os.path.getmtime(full), full))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][1]


def get_video_codec(path):
    """Return codec name using ffprobe, or 'unknown'."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    out, err, code = run_command(cmd)
    if code != 0:
        return "unknown"
    return out.strip() or "unknown"


def convert_vp9(path, choice, log_func):
    base, ext = os.path.splitext(path)

    if choice == "1":  # ProRes 422 HQ
        output = f"{base}_PRORES_HQ.mov"
        cmd = [
            "ffmpeg", "-i", path,
            "-c:v", "prores_ks",
            "-profile:v", "3",
            "-pix_fmt", "yuv422p10le",
            "-c:a", "pcm_s16le",
            output,
        ]
        log_func("🎬 Конвертация в ProRes 422 HQ...")
    elif choice == "2":  # ProRes Proxy
        output = f"{base}_PRORES_PROXY.mov"
        cmd = [
            "ffmpeg", "-i", path,
            "-c:v", "prores_ks",
            "-profile:v", "0",
            "-pix_fmt", "yuv422p10le",
            "-c:a", "pcm_s16le",
            output,
        ]
        log_func("🎬 Конвертация в ProRes Proxy...")
    elif choice == "3":  # H.264
        output = f"{base}_H264.mp4"
        cmd = [
            "ffmpeg", "-i", path,
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac",
            output,
        ]
        log_func("🎬 Конвертация в H.264 MP4...")
    elif choice == "4":  # HEVC
        output = f"{base}_HEVC.mp4"
        cmd = [
            "ffmpeg", "-i", path,
            "-c:v", "libx265",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac",
            output,
        ]
        log_func("🎬 Конвертация в HEVC MP4...")
    else:
        log_func("❌ Неверный выбор, конвертация отменена.")
        return

    out, err, code = run_command(cmd)
    if out:
        log_func(out.strip())
    if err:
        log_func(err.strip())
    if code == 0:
        log_func(f"✅ Готово: {output}")
    else:
        log_func("❌ Ошибка конвертации. См. лог выше.")


def build_format_string(quality_choice):
    if quality_choice == "Максимальное":
        return "bestvideo+bestaudio"
    elif quality_choice == "1080p":
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif quality_choice == "720p":
        return "bestvideo[height<=720]+bestaudio/best[height<=720]"
    else:
        return "bestvideo+bestaudio"


def download_worker(url, fmt_choice, quality_choice, log_func, done_callback):
    try:
        if not url.strip():
            log_func("❌ Введите ссылку на YouTube.")
            return

        log_func("====================================")
        log_func("       YT Downloader Pro Max")
        log_func("====================================")
        log_func(f"Ссылка: {url}")
        log_func(f"Формат: {fmt_choice}")
        log_func(f"Качество: {quality_choice}")
        log_func(f"Папка загрузки: {DOWNLOAD_DIR}")
        log_func("")

        fmt_str = build_format_string(quality_choice)
        out_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

        # ---------- DOWNLOAD ----------
        log_func("⬇️  Скачиваю...")

        if fmt_choice == "MP4":
            cmd = [
                "yt-dlp",
                "-f", fmt_str,
                "-o", out_template,
                url,
                "--merge-output-format", "mp4",
            ]
        elif fmt_choice == "WEBM":
            cmd = [
                "yt-dlp",
                "-f", fmt_str,
                "-o", out_template,
                url,
            ]
        elif fmt_choice == "AUDIO":
            cmd = [
                "yt-dlp",
                "-f", "bestaudio",
                "-o", out_template,
                url,
                "--extract-audio",
                "--audio-format", "mp3",
            ]
        else:
            log_func("❌ Неверный выбор формата.")
            return

        out, err, code = run_command(cmd)
        if out:
            log_func("yt-dlp stdout:\n" + out.strip())
        if err:
            log_func("yt-dlp stderr:\n" + err.strip())
        if code != 0:
            log_func("❌ Ошибка при скачивании. Проверьте лог.")
            return

        last_file = find_last_downloaded_file(DOWNLOAD_DIR)
        if not last_file:
            log_func("❌ Не удалось найти скачанный файл.")
            return

        log_func(f"📁 Последний файл: {last_file}")

        # ---------- POST-PROCESS ----------
        ext = os.path.splitext(last_file)[1].lower()

        if fmt_choice == "AUDIO":
            log_func("🎧 Скачан аудиофайл (mp3/m4a). Готово.")
            return

        if fmt_choice == "WEBM":
            log_func("🎥 WEBM скачан. Готово.")
            return

        if fmt_choice == "MP4":
            # Проверяем кодек
            codec = get_video_codec(last_file)
            log_func(f"🔍 Кодек видео: {codec}")

            if codec.lower() == "vp9":
                def ask_conversion():
                    return simpledialog.askstring(
                        "Обнаружен VP9",
                        "⚡ Видео в кодеке VP9.\n"
                        "Выберите конвертацию:\n"
                        "1) ProRes 422 HQ (очень большой файл)\n"
                        "2) ProRes Proxy (меньше, для монтажа)\n"
                        "3) H.264 MP4 (Premiere читает сразу)\n"
                        "4) HEVC MP4 (меньше, но требует новый софт)\n\n"
                        "Введите цифру (1-4):"
                    )

                choice = ask_conversion()
                if choice:
                    convert_vp9(last_file, choice, log_func)
                else:
                    log_func("Конвертация отменена пользователем.")
            else:
                log_func("✅ Видео уже в подходящем кодеке. Готово.")

    finally:
        done_callback()


# ---------- GUI ----------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT Downloader Pro Max")
        self.geometry("700x500")
        self.minsize(650, 450)

        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="MP4")
        self.quality_var = tk.StringVar(value="Максимальное")
        self.download_dir_var = tk.StringVar(value=DOWNLOAD_DIR)

        self.worker_thread = None

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # URL
        url_label = ttk.Label(main_frame, text="YouTube URL:")
        url_label.grid(row=0, column=0, sticky="w")

        url_entry = ttk.Entry(main_frame, textvariable=self.url_var)
        url_entry.grid(row=1, column=0, columnspan=3, sticky="we", pady=5)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(2, weight=0)

        # Format
        fmt_label = ttk.Label(main_frame, text="Формат:")
        fmt_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

        fmt_frame = ttk.Frame(main_frame)
        fmt_frame.grid(row=3, column=0, sticky="w")

        for text in ("MP4", "WEBM", "AUDIO"):
            rb = ttk.Radiobutton(
                fmt_frame,
                text=text,
                value=text,
                variable=self.format_var
            )
            rb.pack(side="left", padx=(0, 10))

        # Quality
        q_label = ttk.Label(main_frame, text="Качество:")
        q_label.grid(row=2, column=1, sticky="w", pady=(10, 0))

        q_combo = ttk.Combobox(
            main_frame,
            textvariable=self.quality_var,
            values=["Максимальное", "1080p", "720p"],
            state="readonly",
            width=15
        )
        q_combo.grid(row=3, column=1, sticky="w")

        # Download dir
        dir_label = ttk.Label(main_frame, text="Папка загрузки:")
        dir_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=5, column=0, columnspan=3, sticky="we", pady=5)

        dir_entry = ttk.Entry(dir_frame, textvariable=self.download_dir_var)
        dir_entry.pack(side="left", fill="x", expand=True)

        dir_btn = ttk.Button(dir_frame, text="Выбрать...", command=self.choose_dir)
        dir_btn.pack(side="left", padx=(5, 0))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, sticky="we", pady=(10, 5))

        self.download_btn = ttk.Button(
            btn_frame,
            text="Скачать",
            command=self.start_download
        )
        self.download_btn.pack(side="left")

        open_dir_btn = ttk.Button(
            btn_frame,
            text="Открыть папку",
            command=self.open_download_dir
        )
        open_dir_btn.pack(side="left", padx=(5, 0))

        # Status text
        status_label = ttk.Label(main_frame, text="Лог:")
        status_label.grid(row=7, column=0, sticky="w")

        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(5, 0))
        main_frame.rowconfigure(8, weight=1)

        self.status_text = tk.Text(status_frame, height=10, state="disabled", wrap="word")
        self.status_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scroll.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scroll.set)

        # Footer / Instagram
        footer_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        footer_frame.pack(fill="x")

        ig_label = tk.Label(
            footer_frame,
            text="Made by @shoxrux.edit",
            fg="#1a73e8",
            cursor="hand2"
        )
        ig_label.pack(side="right")
        ig_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.instagram.com/shoxrux.edit/"))

    def choose_dir(self):
        path = filedialog.askdirectory(initialdir=self.download_dir_var.get() or os.path.expanduser("~"))
        if path:
            self.download_dir_var.set(path)
            global DOWNLOAD_DIR
            DOWNLOAD_DIR = path
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    def open_download_dir(self):
        path = self.download_dir_var.get()
        if not os.path.isdir(path):
            messagebox.showerror("Ошибка", "Папка загрузки не существует.")
            return
        try:
            os.startfile(path)
        except AttributeError:
            # not Windows, fallback
            subprocess.Popen(["xdg-open", path])

    def log(self, msg):
        def inner():
            self.status_text.config(state="normal")
            self.status_text.insert("end", msg + "\n")
            self.status_text.see("end")
            self.status_text.config(state="disabled")
        self.after(0, inner)

    def set_buttons_state(self, enabled: bool):
        def inner():
            state = "normal" if enabled else "disabled"
            self.download_btn.config(state=state)
        self.after(0, inner)

    def start_download(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Загрузка", "Загрузка уже идёт. Подожди окончания.")
            return

        url = self.url_var.get().strip()
        fmt = self.format_var.get()
        quality = self.quality_var.get()

        if not url:
            messagebox.showerror("Ошибка", "Вставь ссылку на YouTube.")
            return

        global DOWNLOAD_DIR
        DOWNLOAD_DIR = self.download_dir_var.get().strip() or get_default_download_dir()
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        self.set_buttons_state(False)

        def done():
            self.set_buttons_state(True)
            self.log("🎉 Всё завершено!")

        self.worker_thread = threading.Thread(
            target=download_worker,
            args=(url, fmt, quality, self.log, done),
            daemon=True
        )
        self.worker_thread.start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
