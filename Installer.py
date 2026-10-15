import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "YDL"
FONT = "Yu Gothic UI"
AUTHOR = "すも"
AUTHOR_URL = "https://github.com/Sumomodayo/youtube_downloader"
PAD = 24
TOTAL_STEPS = 5
NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\YDL"

STRIP_ENV = ("_MEIPASS2", "PYTHONHOME", "PYTHONPATH",
             "TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH", "TIX_LIBRARY")

RUNTIME_HOOK = '''import os, sys
_base = getattr(sys, "_MEIPASS", None)
if _base:
    _tcl = os.path.join(_base, "_tcl_data")
    _tk = os.path.join(_base, "_tk_data")
    if os.path.isfile(os.path.join(_tcl, "init.tcl")):
        os.environ["TCL_LIBRARY"] = _tcl
    if os.path.isdir(_tk):
        os.environ["TK_LIBRARY"] = _tk
'''

TCL_PROBE = (
    "import os, tkinter\n"
    "t = tkinter.Tcl()\n"
    "tcl = os.path.normpath(t.eval('info library'))\n"
    "tk = os.path.normpath(os.path.join(os.path.dirname(tcl), 'tk%s' % tkinter.TkVersion))\n"
    "print(tcl)\n"
    "print(tk)\n"
)

PAGE_NAMES = ["同意", "オプション", "インストール先", "インストール"]

C = dict(
    bg="#171A23",
    panel="#222636",
    line="#343A50",
    text="#ECEEF5",
    muted="#8C94AB",
    faint="#4A5068",
    accent="#9B8CFF",
    on_accent="#12101F",
    error="#FF7A8A",
)

TERMS = [
    ("■ 1. 個人制作ソフトウェアについて", [
        "YDL（YouTube ダウンローダー）は、個人が制作したソフトウェアです。",
        "本ソフトウェアの使用は、利用者自身の責任で行ってください。",
    ]),
    ("■ 2. ダウンロードに関する注意", [
        "本ソフトウェアは、YouTubeの動画から音声（MP3）または動画（MP4）を取得するためのツールです。",
        "ダウンロードは、著作権法およびYouTubeの利用規約を守って行ってください。",
        "自分で投稿した動画や、権利者からダウンロードの許可を得ている動画など、利用する権利があるコンテンツを対象としています。",
        "第三者が権利を持つコンテンツを、許可なくダウンロード・複製・配布・公開することは避けてください。",
    ]),
    ("■ 3. 免責事項", [
        "本ソフトウェアの使用によって発生した損害、トラブル、データの損失などについて、制作者は責任を負いません。",
        "本ソフトウェアの正常な動作、継続的な提供、すべての動画への対応を保証するものではありません。",
        "YouTubeの仕様変更などにより、予告なく一部または全部の機能が使用できなくなる場合があります。",
    ]),
    ("■ 4. 再配布・改変について", [
        "本ソフトウェアの再配布、改変、商用利用については、制作者が別途定める条件に従ってください。",
        "明示的な許可がない場合、制作者の配布物を自分の作品として公開しないでください。",
    ]),
    ("■ 5. 利用について", [
        "本ソフトウェアを使用した時点で、利用者は本注意事項を確認したものとします。",
    ]),
]

def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def clean_env() -> dict:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("_PYI") or key in STRIP_ENV:
            env.pop(key, None)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        target = os.path.normcase(os.path.normpath(meipass))
        parts = [p for p in env.get("PATH", "").split(os.pathsep)
                 if p and os.path.normcase(os.path.normpath(p)) != target]
        env["PATH"] = os.pathsep.join(parts)

    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def launch_app(exe: str):
    subprocess.Popen([exe], cwd=os.path.dirname(exe), env=clean_env(),
                     creationflags=DETACHED, close_fds=True)

def find_python():
    for cmd in (["py", "-3"], ["python"], ["python3"]):
        try:
            r = subprocess.run(
                cmd + ["-c", "import sys, tkinter; print(sys.version_info[0])"],
                capture_output=True, text=True, env=clean_env(),
                creationflags=NO_WINDOW, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0 and r.stdout.strip() == "3":
            return cmd
    return None

def find_tcl_dirs(py):
    try:
        r = subprocess.run(py + ["-c", TCL_PROBE], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=clean_env(),
                           creationflags=NO_WINDOW, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    tcl, tk_dir = lines[-2], lines[-1]
    if os.path.isfile(os.path.join(tcl, "init.tcl")) and \
            os.path.isfile(os.path.join(tk_dir, "tk.tcl")):
        return tcl, tk_dir
    return None

def register_uninstall(install_dir: str):
    import winreg
    exe = os.path.join(install_dir, "YDL.exe")
    uninstaller = os.path.join(install_dir, "YDL-uninstaller.exe")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "YDL (YouTube ダウンローダー)")
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}"')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

def create_desktop_shortcut(target: str):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
          "(Join-Path ([Environment]::GetFolderPath('Desktop')) 'YDL.lnk')); "
          "$s.TargetPath=$env:YDL_TARGET; "
          "$s.WorkingDirectory=(Split-Path $env:YDL_TARGET); "
          "$s.IconLocation=$env:YDL_TARGET; $s.Save()")
    env = clean_env()
    env["YDL_TARGET"] = target
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env,
                   creationflags=NO_WINDOW, check=True, capture_output=True)

class BuildError(Exception):
    pass

class PythonMissing(BuildError):
    pass

class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YDL セットアップ")
        self.configure(bg=C["bg"])
        self.geometry("560x570")
        self.resizable(False, False)
        try:
            self.iconbitmap(resource_path("icon.ico"))
        except tk.TclError:
            pass

        self.events = queue.Queue()
        self.proc = None
        self.work_dir = None
        self.running = False
        self.cancelled = False
        self.done = False
        self.launch_exe = None
        self.page = 0

        self.var_shortcut = tk.BooleanVar(value=True)
        self.var_launch = tk.BooleanVar(value=True)
        self.install_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", APP_NAME)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Setup.Horizontal.TProgressbar",
                        troughcolor=C["panel"], background=C["accent"],
                        bordercolor=C["bg"], lightcolor=C["accent"],
                        darkcolor=C["accent"], thickness=6)
        style.configure("Setup.Vertical.TScrollbar",
                        troughcolor=C["panel"], background=C["line"],
                        bordercolor=C["panel"], lightcolor=C["line"],
                        darkcolor=C["line"], arrowcolor=C["muted"])

        self._build()
        self.show_page(0)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.poll)

    def _heading(self, parent, title, sub=None):
        tk.Label(parent, text=title, font=(FONT, 13, "bold"), bg=C["bg"],
                 fg=C["text"], anchor="w").pack(fill="x")
        if sub:
            tk.Label(parent, text=sub, font=(FONT, 9), bg=C["bg"], fg=C["muted"],
                     anchor="w", wraplength=500, justify="left").pack(fill="x", pady=(4, 0))

    def _check(self, parent, text, var):
        cb = tk.Checkbutton(parent, text=text, variable=var,
                            font=(FONT, 10), bg=C["bg"], fg=C["text"],
                            selectcolor=C["panel"], activebackground=C["bg"],
                            activeforeground=C["text"], highlightthickness=0, bd=0,
                            anchor="w", cursor="hand2")
        cb.pack(fill="x", pady=3)
        return cb

    def _nav_btn(self, parent, command):
        return tk.Button(parent, text="", font=(FONT, 9), relief="flat", bd=0,
                         padx=14, pady=4, cursor="hand2", command=command)

    def _style_btn(self, btn, text, enabled, primary):
        if not enabled:
            btn.config(text=text, state="disabled", bg=C["panel"], fg=C["faint"],
                       disabledforeground=C["faint"], cursor="arrow")
        elif primary:
            btn.config(text=text, state="normal", bg=C["accent"], fg=C["on_accent"],
                       activebackground=C["accent"], activeforeground=C["on_accent"],
                       cursor="hand2")
        else:
            btn.config(text=text, state="normal", bg=C["panel"], fg=C["text"],
                       activebackground=C["line"], activeforeground=C["text"],
                       cursor="hand2")

    def _build(self):
        tk.Label(self, text="YDL セットアップ", font=(FONT, 16, "bold"),
                 bg=C["bg"], fg=C["text"], anchor="w").pack(fill="x", padx=PAD, pady=(22, 8))

        self.steps_row = tk.Frame(self, bg=C["bg"])
        self.steps_row.pack(fill="x", padx=PAD)
        self.step_labels = []
        for i, name in enumerate(PAGE_NAMES):
            lbl = tk.Label(self.steps_row, text=f"{i + 1} {name}", font=(FONT, 9),
                           bg=C["bg"], fg=C["faint"])
            lbl.pack(side="left")
            self.step_labels.append(lbl)
            if i < len(PAGE_NAMES) - 1:
                tk.Label(self.steps_row, text="  ›  ", font=(FONT, 9),
                         bg=C["bg"], fg=C["line"]).pack(side="left")

        tk.Frame(self, bg=C["line"], height=1).pack(fill="x", padx=PAD, pady=(14, 0))

        self.author = tk.Label(self, text=AUTHOR, font=(FONT, 8), bg=C["bg"],
                               fg=C["faint"], anchor="e", cursor="hand2")
        self.author.pack(side="bottom", fill="x", padx=PAD, pady=(0, 10))
        self.author.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))
        self.author.bind("<Enter>", lambda e: self.author.config(fg=C["muted"]))
        self.author.bind("<Leave>", lambda e: self.author.config(fg=C["faint"]))

        nav = tk.Frame(self, bg=C["bg"])
        nav.pack(side="bottom", fill="x", padx=PAD, pady=(8, 8))
        self.next_btn = self._nav_btn(nav, self.go_next)
        self.next_btn.pack(side="right")
        self.back_btn = self._nav_btn(nav, self.go_back)
        self.back_btn.pack(side="right", padx=(0, 6))

        self.body = tk.Frame(self, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=PAD, pady=(16, 0))

        self.pages = [
            self._page_terms(),
            self._page_options(),
            self._page_location(),
            self._page_install(),
        ]

    def _page_terms(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, "利用規約・注意事項",
                      "内容をお読みのうえ、同意する場合は「同意する」を押してください。")

        box = tk.Frame(f, bg=C["panel"], highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="both", expand=True, pady=(12, 0))
        sb = ttk.Scrollbar(box, style="Setup.Vertical.TScrollbar", orient="vertical")
        sb.pack(side="right", fill="y")
        txt = tk.Text(box, bg=C["panel"], fg=C["text"], font=(FONT, 9), relief="flat", bd=0,
                      wrap="word", padx=12, pady=10, spacing3=3, cursor="arrow",
                      yscrollcommand=sb.set, highlightthickness=0)
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        txt.tag_configure("h", font=(FONT, 10, "bold"), foreground=C["accent"],
                          spacing1=8, spacing3=4)
        for heading, lines in TERMS:
            txt.insert("end", heading + "\n", "h")
            for line in lines:
                txt.insert("end", line + "\n")
        txt.config(state="disabled")
        return f

    def _page_options(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, "オプションの選択", "インストール時の追加設定を選んでください。")
        opts = tk.Frame(f, bg=C["bg"])
        opts.pack(fill="x", pady=(16, 0))
        self.chk_shortcut = self._check(opts, "デスクトップにショートカットを作成する",
                                        self.var_shortcut)
        self.chk_launch = self._check(opts, "完了したら YDL を起動する", self.var_launch)
        return f

    def _page_location(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, "インストール先の選択", "YDL をインストールするフォルダを選んでください。")
        row = tk.Frame(f, bg=C["bg"])
        row.pack(fill="x", pady=(16, 0))
        self.path_label = tk.Label(row, text=self.install_dir, font=(FONT, 9), bg=C["panel"],
                                   fg=C["text"], anchor="w", wraplength=380, justify="left",
                                   padx=10, pady=8)
        self.path_label.pack(side="left", fill="x", expand=True)
        self.change_btn = tk.Button(row, text="変更", font=(FONT, 9), relief="flat", bd=0,
                                    bg=C["panel"], fg=C["text"], activebackground=C["line"],
                                    activeforeground=C["text"], cursor="hand2", padx=14,
                                    command=self.choose_dir)
        self.change_btn.pack(side="right", fill="y", padx=(6, 0))
        tk.Label(f, text="インストールにはビルドを行うため、数分かかります。",
                 font=(FONT, 9), bg=C["bg"], fg=C["muted"], anchor="w").pack(fill="x", pady=(12, 0))
        return f

    def _page_install(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, "インストール")
        self.bar = ttk.Progressbar(f, style="Setup.Horizontal.TProgressbar",
                                   maximum=100, mode="determinate")
        self.bar.pack(fill="x", pady=(14, 6))
        self.step_label = tk.Label(f, text="準備しています…", font=(FONT, 9),
                                   bg=C["bg"], fg=C["muted"], anchor="w",
                                   wraplength=500, justify="left")
        self.step_label.pack(fill="x")
        self.log_text = tk.Text(f, height=10, bg=C["panel"], fg=C["muted"],
                                font=("Consolas", 9), relief="flat", bd=0, wrap="char",
                                highlightthickness=1, highlightbackground=C["line"],
                                state="disabled", padx=8, pady=6)
        self.log_text.pack(fill="both", expand=True, pady=(10, 0))
        return f

    def show_page(self, n):
        self.page = n
        for p in self.pages:
            p.pack_forget()
        self.pages[n].pack(fill="both", expand=True)
        for i, lbl in enumerate(self.step_labels):
            if i == n:
                lbl.config(fg=C["accent"], font=(FONT, 9, "bold"))
            else:
                lbl.config(fg=C["muted"] if i < n else C["faint"], font=(FONT, 9))
        self.update_nav()

    def update_nav(self):
        p = self.page
        if p == 0:
            self._style_btn(self.back_btn, "同意しない", True, False)
            self._style_btn(self.next_btn, "同意する", True, True)
        elif p == 1:
            self._style_btn(self.back_btn, "戻る", True, False)
            self._style_btn(self.next_btn, "次へ", True, True)
        elif p == 2:
            self._style_btn(self.back_btn, "戻る", True, False)
            self._style_btn(self.next_btn, "インストール", True, True)
        else:
            if self.running:
                self._style_btn(self.back_btn, "戻る", False, False)
                self._style_btn(self.next_btn, "インストール中…", False, True)
            elif self.done:
                self._style_btn(self.back_btn, "戻る", False, False)
                self._style_btn(self.next_btn, "完了", True, True)
            else:
                self._style_btn(self.back_btn, "戻る", True, False)
                self._style_btn(self.next_btn, "もう一度", True, True)

    def go_next(self):
        p = self.page
        if p < 2:
            self.show_page(p + 1)
        elif p == 2:
            self.show_page(3)
            self.start()
        else:
            if self.done:
                self.finish()
            elif not self.running:
                self.start()

    def finish(self):
        if self.launch_exe:
            try:
                launch_app(self.launch_exe)
            except OSError as e:
                messagebox.showerror("起動に失敗", f"YDL を起動できませんでした:\n{e}")
        self.destroy()

    def go_back(self):
        if self.running:
            return
        if self.page == 0:
            if messagebox.askyesno("セットアップを終了", "同意しない場合はインストールできません。\n終了しますか？"):
                self.destroy()
            return
        self.show_page(self.page - 1)

    def append_log(self, line):
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        if int(self.log_text.index("end-1c").split(".")[0]) > 400:
            self.log_text.delete("1.0", "2.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def choose_dir(self):
        if self.running:
            return
        initial = os.path.dirname(self.install_dir)
        path = filedialog.askdirectory(
            title="インストール先のフォルダを選択",
            initialdir=initial if os.path.isdir(initial) else os.path.expanduser("~"))
        if not path:
            return
        path = os.path.normpath(path)

        if os.path.basename(path).lower() != APP_NAME.lower():
            path = os.path.join(path, APP_NAME)
        self.install_dir = path
        self.path_label.config(text=path)

    def start(self):
        if self.running:
            return
        self.running = True
        self.cancelled = False
        self.done = False
        self.launch_exe = None
        self.clear_log()
        self.step_label.config(text="準備しています…", fg=C["muted"])
        self.bar.config(mode="indeterminate")
        self.bar.start(12)
        self.update_nav()

        options = dict(shortcut=self.var_shortcut.get(), launch=self.var_launch.get())
        threading.Thread(target=self.worker, args=(options,), daemon=True).start()

    def on_close(self):
        if self.running:
            if not messagebox.askyesno("インストール中です", "インストールを中止して閉じますか？"):
                return
            self.cancelled = True
            if self.proc is not None:
                try:
                    self.proc.terminate()
                except OSError:
                    pass
            if self.work_dir:
                shutil.rmtree(self.work_dir, ignore_errors=True)
        self.destroy()

    def log(self, text):
        self.events.put(("log", text))

    def step(self, n, text):
        self.events.put(("step", n, text))

    def run(self, cmd, cwd):
        self.proc = subprocess.Popen(
            cmd, cwd=cwd, env=clean_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        for line in self.proc.stdout:
            line = line.rstrip()
            if line:
                self.log(line)
        code = self.proc.wait()
        self.proc = None
        if self.cancelled:
            raise BuildError("中止しました")
        if code != 0:
            raise BuildError(f"コマンドが失敗しました（終了コード {code}）。ログを確認してください。")

    def worker(self, options):
        work = tempfile.mkdtemp(prefix="ydl_build_")
        self.work_dir = work
        try:

            self.step(1, "Python を確認しています")
            py = find_python()
            if py is None:
                raise PythonMissing("tkinter 付きの Python 3 が見つかりません。")
            self.log("Python: " + " ".join(py))

            self.step(2, "必要なライブラリをインストールしています")
            self.run(py + ["-m", "pip", "install", "-U", "--disable-pip-version-check",
                           "--progress-bar", "off", "yt-dlp", "imageio-ffmpeg", "pyinstaller"],
                     work)

            src = os.path.join(work, "src")
            os.makedirs(src, exist_ok=True)
            for name in ("main.py", "uninstall.py", "icon.ico"):
                shutil.copy2(resource_path(name), os.path.join(src, name))
            hook = os.path.join(src, "ydl_tcl_hook.py")
            with open(hook, "w", encoding="utf-8") as f:
                f.write(RUNTIME_HOOK)
            ico = os.path.join(src, "icon.ico")

            dist = os.path.join(work, "dist")
            common = ["-m", "PyInstaller", "--onefile", "--noconsole", "--clean", "--noconfirm",
                      "--log-level", "WARN", "--distpath", dist,
                      "--workpath", os.path.join(work, "build"), "--specpath", work,
                      "--icon", ico]

            tcl_extra = []
            tcl = find_tcl_dirs(py)
            if tcl:
                self.log(f"Tcl: {tcl[0]}")
                self.log(f"Tk : {tcl[1]}")
                tcl_extra = ["--add-data", f"{tcl[0]};_tcl_data",
                             "--add-data", f"{tcl[1]};_tk_data",
                             "--runtime-hook", hook]
            else:
                self.log("（Tcl/Tk の場所を特定できませんでした。PyInstaller の自動検出に任せます）")

            self.step(3, "YDL.exe をビルドしています（数分かかります）")
            self.run(py + common + ["--name", "YDL", "--add-data", f"{ico};.",
                                    "--hidden-import=yt_dlp", "--collect-all", "imageio_ffmpeg"]
                     + tcl_extra + [os.path.join(src, "main.py")], work)

            self.step(4, "YDL-uninstaller.exe をビルドしています")
            self.run(py + common + ["--name", "YDL-uninstaller",
                                    os.path.join(src, "uninstall.py")], work)

            self.step(5, "インストールしています")
            try:
                os.makedirs(self.install_dir, exist_ok=True)
            except OSError as e:
                raise BuildError(f"インストール先を作成できません: {e}\n"
                                 "「戻る」で別の場所（書き込めるフォルダ）を選んでください。")
            for name in ("YDL.exe", "YDL-uninstaller.exe"):
                exe_src = os.path.join(dist, name)
                if not os.path.exists(exe_src):
                    raise BuildError(f"{name} が作成されませんでした。ログを確認してください。")
                try:
                    shutil.copy2(exe_src, os.path.join(self.install_dir, name))
                except PermissionError:
                    raise BuildError("YDL が起動している可能性があります。"
                                     "YDL を終了してから、もう一度実行してください。")
                self.log(f"コピーしました: {name}")

            try:
                register_uninstall(self.install_dir)
                self.log("「設定 > アプリ」に登録しました")
            except Exception as e:
                self.log(f"（アプリ一覧への登録に失敗しました: {e}）")

            exe = os.path.join(self.install_dir, "YDL.exe")
            if options["shortcut"]:
                try:
                    create_desktop_shortcut(exe)
                    self.log("デスクトップにショートカットを作成しました")
                except Exception as e:
                    self.log(f"（ショートカットの作成に失敗しました: {e}）")

            self.events.put(("done", exe, options["launch"]))
        except PythonMissing as e:
            self.events.put(("error", str(e), True))
        except Exception as e:
            self.events.put(("error", str(e), False))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "log":
                    self.append_log(ev[1])
                elif kind == "step":
                    self.step_label.config(
                        text=f"ステップ {ev[1]} / {TOTAL_STEPS}  {ev[2]}", fg=C["muted"])
                    self.append_log(f"=== {ev[1]}/{TOTAL_STEPS}  {ev[2]} ===")
                elif kind == "done":
                    self.on_done(ev[1], ev[2])
                elif kind == "error":
                    self.on_error(ev[1], ev[2])
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def finish_progress(self):
        self.running = False
        self.bar.stop()
        self.bar.config(mode="determinate")

    def on_done(self, exe, launch):
        self.finish_progress()
        self.done = True
        self.launch_exe = exe if launch else None
        self.bar["value"] = 100
        msg = "インストールが完了しました。"
        msg += "「完了」を押すと YDL が起動します。" if launch else "「完了」を押して閉じてください。"
        self.step_label.config(text=msg, fg=C["accent"])
        self.append_log(f"完了: {exe}")
        self.update_nav()

    def on_error(self, message, python_missing):
        self.finish_progress()
        self.bar["value"] = 0
        self.step_label.config(text="失敗しました: " + message, fg=C["error"])
        self.append_log("失敗: " + message)
        self.update_nav()

        if python_missing:
            if messagebox.askyesno(
                    "Python が必要です",
                    "ビルドには Python 3 が必要です。\n\n"
                    "Python のダウンロードページを開きますか？\n\n"
                    "インストールのときは、次の2点に注意してください。\n"
                    "・「Add python.exe to PATH」にチェックを入れる\n"
                    "・「tcl/tk and IDLE」を外さない"):
                webbrowser.open("https://www.python.org/downloads/")

if __name__ == "__main__":
    Installer().mainloop()