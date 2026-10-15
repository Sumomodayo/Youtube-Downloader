# pip install yt-dlp imageio-ffmpeg pyinstaller
# python -m PyInstaller --onefile --noconsole --clean --name YDL --icon icon.ico --add-data "icon.ico;." --hidden-import=yt_dlp --collect-all imageio_ffmpeg main.py

import os
import re
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import yt_dlp
import imageio_ffmpeg as ffmpeg

FONT = "Yu Gothic UI"
AUTHOR = "すも"
AUTHOR_URL = "https://github.com/Sumomodayo/Youtube-Downloader"

C = dict(
    bg="#171A23",
    panel="#222636",
    line="#343A50",
    text="#ECEEF5",
    muted="#8C94AB",
    faint="#4A5068",
    error="#FF7A8A",
)

MODES = {
    "mp3": dict(
        label="MP3  音声",
        accent="#9B8CFF",
        on_accent="#12101F",
        quality_title="音質",
        default="192",
        options=[("128k", "128"), ("192k", "192"), ("256k", "256"), ("320k", "320")],
    ),
    "mp4": dict(
        label="MP4  動画",
        accent="#4CC4F5",
        on_accent="#07202B",
        quality_title="画質（最大）",
        default="1080",
        options=[("360p", "360"), ("480p", "480"), ("720p", "720"),
                 ("1080p", "1080"), ("1440p", "1440"), ("4K", "2160")],
    ),
}

PAD = 24
DEFAULT_FOLDER = "YDL"

def clean_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip().rstrip(".")
    return name.replace("%", "%%")


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def shorten(path: str, limit: int = 40) -> str:
    return path if len(path) <= limit else "…" + path[-(limit - 1):]

def build_options(mode, quality, outtmpl, on_progress, on_post, thumbnail=False):
    opts = {
        "ffmpeg_location": ffmpeg.get_ffmpeg_exe(),
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [on_progress],
        "postprocessor_hooks": [on_post],
    }
    if mode == "mp3":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }],
        })
    else:
        opts.update({
            "format": (f"bestvideo[ext=mp4][height<={quality}]+bestaudio[ext=m4a]"
                       f"/best[ext=mp4][height<={quality}]/best"),
            "merge_output_format": "mp4",
            "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        })
    if thumbnail:
        opts["writethumbnail"] = True
        opts["postprocessors"].append({
            "key": "FFmpegThumbnailsConvertor",
            "format": "jpg",
            "when": "before_dl",
        })
    return opts

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube ダウンローダー V1.0.0")
        try:
            self.iconbitmap(resource_path("icon.ico"))
        except tk.TclError:
            pass
        self.configure(bg=C["bg"])
        self.geometry("460x660")
        self.resizable(False, False)

        self.mode = "mp3"
        self.quality = {k: m["default"] for k, m in MODES.items()}
        self.custom_dir = None
        self.last_dir = None
        self.busy = False
        self.entries = []
        self.var_thumb = tk.BooleanVar(value=False)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self._build()
        self.set_mode("mp3")

    def _label(self, text):
        lbl = tk.Label(self, text=text, font=(FONT, 9), bg=C["bg"], fg=C["muted"], anchor="w")
        lbl.pack(fill="x", padx=PAD, pady=(16, 5))
        return lbl

    def _entry(self, parent):
        e = tk.Entry(parent, font=(FONT, 11), bg=C["panel"], fg=C["text"],
                     insertbackground=C["text"], relief="flat",
                     highlightthickness=1, highlightbackground=C["line"])
        self.entries.append(e)
        return e

    def _build(self):
        tk.Label(self, text="YouTube ダウンローダー", font=(FONT, 16, "bold"),
                 bg=C["bg"], fg=C["text"], anchor="w").pack(fill="x", padx=PAD, pady=(24, 14))

        toggle = tk.Frame(self, bg=C["panel"])
        toggle.pack(fill="x", padx=PAD)
        self.mode_btns = {}
        for i, (key, m) in enumerate(MODES.items()):
            b = tk.Button(toggle, text=m["label"], font=(FONT, 11, "bold"),
                          relief="flat", bd=0, pady=9, cursor="hand2",
                          command=lambda k=key: self.set_mode(k))
            b.grid(row=0, column=i, sticky="ew", padx=3, pady=3)
            toggle.columnconfigure(i, weight=1)
            self.mode_btns[key] = b

        self._label("YouTube の URL")
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x", padx=PAD)
        self.url_entry = self._entry(row)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(row, text="貼り付け", font=(FONT, 9), relief="flat", bd=0,
                  bg=C["panel"], fg=C["text"], activebackground=C["line"],
                  activeforeground=C["text"], cursor="hand2", padx=12,
                  command=self.paste_url).pack(side="left", fill="y", padx=(6, 0))

        self.quality_title = self._label("")
        self.chips = tk.Frame(self, bg=C["bg"])
        self.chips.pack(fill="x", padx=PAD)

        self._label("ファイル名（空欄なら元動画のタイトル）")
        self.name_entry = self._entry(self)
        self.name_entry.pack(fill="x", padx=PAD, ipady=7)

        self.chk_thumb = tk.Checkbutton(
            self, text="サムネイルも保存する（jpg・同じ保存先／ファイル名）",
            variable=self.var_thumb, font=(FONT, 10),
            bg=C["bg"], fg=C["text"], selectcolor=C["panel"],
            activebackground=C["bg"], activeforeground=C["text"],
            highlightthickness=0, bd=0, anchor="w", cursor="hand2")
        self.chk_thumb.pack(fill="x", padx=PAD - 2, pady=(12, 0))

        self._label("保存先")
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x", padx=PAD)
        self.path_label = tk.Label(row, font=(FONT, 9), bg=C["bg"], fg=C["text"], anchor="w")
        self.path_label.pack(side="left", fill="x", expand=True)
        tk.Button(row, text="変更", font=(FONT, 9), relief="flat", bd=0,
                  bg=C["panel"], fg=C["text"], activebackground=C["line"],
                  activeforeground=C["text"], cursor="hand2", padx=14,
                  command=self.choose_dir).pack(side="right")

        self.bar = ttk.Progressbar(self, style="Bar.Horizontal.TProgressbar",
                                   maximum=100, mode="determinate")
        self.bar.pack(fill="x", padx=PAD, pady=(26, 6))
        status_row = tk.Frame(self, bg=C["bg"])
        status_row.pack(fill="x", padx=PAD)
        self.status = tk.Label(status_row, text="", font=(FONT, 9), bg=C["bg"],
                               fg=C["muted"], anchor="w", justify="left", wraplength=300)
        self.status.pack(side="left", fill="x", expand=True)
        self.open_btn = tk.Button(status_row, text="フォルダを開く", font=(FONT, 9),
                                  relief="flat", bd=0, bg=C["panel"], fg=C["text"],
                                  activebackground=C["line"], activeforeground=C["text"],
                                  cursor="hand2", padx=10, command=self.open_folder)

        self.author = tk.Label(self, text=AUTHOR, font=(FONT, 8), bg=C["bg"],
                               fg=C["faint"], anchor="e", cursor="hand2")
        self.author.pack(side="bottom", fill="x", padx=PAD, pady=(0, 10))
        self.author.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))
        self.author.bind("<Enter>", lambda e: self.author.config(fg=C["muted"]))
        self.author.bind("<Leave>", lambda e: self.author.config(fg=C["faint"]))

        self.go_btn = tk.Button(self, text="ダウンロード", font=(FONT, 12, "bold"),
                                relief="flat", bd=0, pady=11, cursor="hand2",
                                command=self.start)
        self.go_btn.pack(side="bottom", fill="x", padx=PAD, pady=(0, 8))

    def set_mode(self, mode):
        if self.busy:
            return
        self.mode = mode
        m = MODES[mode]

        for key, b in self.mode_btns.items():
            on = key == mode
            b.config(bg=m["accent"] if on else C["panel"],
                     fg=m["on_accent"] if on else C["muted"],
                     activebackground=m["accent"] if on else C["panel"],
                     activeforeground=m["on_accent"] if on else C["text"])

        for e in self.entries:
            e.config(highlightcolor=m["accent"])

        self.style.configure("Bar.Horizontal.TProgressbar",
                             troughcolor=C["panel"], background=m["accent"],
                             bordercolor=C["bg"], lightcolor=m["accent"],
                             darkcolor=m["accent"], thickness=6)

        self.quality_title.config(text=m["quality_title"])
        self.render_chips()
        self.update_path_label()
        self.refresh_button()
        self.set_status("", C["muted"])
        self.open_btn.pack_forget()
        self.bar["value"] = 0

    def render_chips(self):
        for w in self.chips.winfo_children():
            w.destroy()
        m = MODES[self.mode]
        for i, (text, value) in enumerate(m["options"]):
            on = self.quality[self.mode] == value
            b = tk.Button(self.chips, text=text, font=(FONT, 10), relief="flat", bd=0,
                          pady=7, cursor="hand2",
                          bg=m["accent"] if on else C["panel"],
                          fg=m["on_accent"] if on else C["text"],
                          activebackground=m["accent"] if on else C["line"],
                          activeforeground=m["on_accent"] if on else C["text"],
                          command=lambda v=value: self.pick_quality(v))
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))
            self.chips.columnconfigure(i, weight=1, uniform="chip")

    def pick_quality(self, value):
        if self.busy:
            return
        self.quality[self.mode] = value
        self.render_chips()

    def refresh_button(self):
        m = MODES[self.mode]
        if self.busy:
            self.go_btn.config(text="ダウンロード中…", state="disabled",
                               bg=C["line"], fg=C["muted"], cursor="arrow",
                               disabledforeground=C["muted"])
        else:
            label = "MP3 をダウンロード" if self.mode == "mp3" else "MP4 をダウンロード"
            self.go_btn.config(text=label, state="normal", bg=m["accent"],
                               fg=m["on_accent"], activebackground=m["accent"],
                               activeforeground=m["on_accent"], cursor="hand2")

    def set_status(self, text, color=None):
        self.status.config(text=text, fg=color or C["muted"])

    def save_dir(self):
        if self.custom_dir:
            return self.custom_dir
        return os.path.join(os.path.expanduser("~"), "Desktop", DEFAULT_FOLDER)

    def update_path_label(self):
        self.path_label.config(text=shorten(self.save_dir()))

    def paste_url(self):
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, text)

    def choose_dir(self):
        path = filedialog.askdirectory(title="保存先を選択", initialdir=self.save_dir()
                                       if os.path.isdir(self.save_dir()) else os.path.expanduser("~"))
        if path:
            self.custom_dir = os.path.normpath(path)
            self.update_path_label()

    def open_folder(self):
        if not self.last_dir:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.last_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.last_dir])
            else:
                subprocess.run(["xdg-open", self.last_dir])
        except OSError:
            pass

    def start(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("入力エラー", "YouTube の URL を入力してください")
            return

        mode = self.mode
        quality = self.quality[mode]
        name = clean_name(self.name_entry.get())
        save_dir = self.save_dir()
        thumbnail = self.var_thumb.get()

        self.busy = True
        self.refresh_button()
        self.bar["value"] = 0
        self.open_btn.pack_forget()
        self.chk_thumb.config(state="disabled")
        self.set_status("準備中…", C["muted"])

        threading.Thread(target=self.worker,
                         args=(url, mode, quality, name, save_dir, thumbnail),
                         daemon=True).start()

    def worker(self, url, mode, quality, name, save_dir, thumbnail):
        def on_progress(d):
            if d["status"] != "downloading":
                return
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if not total:
                return
            pct = d["downloaded_bytes"] / total * 100
            kind = "ダウンロード中"
            if mode == "mp4":
                is_video = (d.get("info_dict") or {}).get("vcodec", "none") != "none"
                kind = "映像を取得中" if is_video else "音声を取得中"
            self.after(0, self.show_progress, pct, f"{kind}  {pct:.0f}%")

        def on_post(d):
            if d["status"] == "started":
                label = "MP3 に変換中…" if mode == "mp3" else "MP4 にまとめています…"
                self.after(0, self.show_progress, 100, label)

        try:
            os.makedirs(save_dir, exist_ok=True)
            base = name if name else "%(title)s"
            outtmpl = os.path.join(save_dir, f"{base}.%(ext)s")
            opts = build_options(mode, quality, outtmpl, on_progress, on_post, thumbnail)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            self.after(0, self.on_done, save_dir, (info or {}).get("title", ""))
        except Exception as e:
            self.after(0, self.on_failed, str(e))

    def show_progress(self, pct, text):
        self.bar["value"] = pct
        self.set_status(text, C["muted"])

    def on_done(self, save_dir, title):
        self.busy = False
        self.last_dir = save_dir
        self.bar["value"] = 100
        self.set_status(f"保存しました\n{title}" if title else "保存しました",
                        MODES[self.mode]["accent"])
        self.open_btn.pack(side="right", anchor="n")
        self.url_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.chk_thumb.config(state="normal")
        self.refresh_button()
        self.open_folder()

    def on_failed(self, message):
        self.busy = False
        self.bar["value"] = 0
        self.set_status("ダウンロードに失敗しました", C["error"])
        self.chk_thumb.config(state="normal")
        self.refresh_button()
        messagebox.showerror("失敗", f"ダウンロードに失敗しました:\n{message}")

if __name__ == "__main__":
    App().mainloop()