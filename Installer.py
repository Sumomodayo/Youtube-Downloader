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

from i18n import Translator, lang_switch
## 1.0.0
APP_NAME = "YDL"
FONT = "Yu Gothic UI"
AUTHOR = "すも"
AUTHOR_URL = "https://github.com/Sumomodayo/Youtube-Downloader"
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

PAGE_KEYS = ["p_agree", "p_options", "p_location", "p_install"]

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

TERMS = {
    "ja": [
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
    ],
    "en": [
        ("■ 1. About this personal software", [
            "YDL (YouTube Downloader) is software created by an individual.",
            "Please use this software at your own responsibility.",
        ]),
        ("■ 2. Notes on downloading", [
            "This software is a tool for obtaining audio (MP3) or video (MP4) from YouTube videos.",
            "Please download only in compliance with copyright law and YouTube's Terms of Service.",
            "It is intended for content you have the right to use, such as videos you uploaded yourself or videos for which the rights holder has granted permission to download.",
            "Please do not download, copy, distribute, or publish content owned by third parties without permission.",
        ]),
        ("■ 3. Disclaimer", [
            "The author is not responsible for any damage, trouble, or data loss arising from the use of this software.",
            "There is no guarantee that this software will work correctly, remain available, or support every video.",
            "Some or all features may stop working without notice due to changes in YouTube, etc.",
        ]),
        ("■ 4. Redistribution and modification", [
            "Redistribution, modification, and commercial use of this software are subject to the conditions separately set by the author.",
            "Without explicit permission, do not publish the author's distributed files as your own work.",
        ]),
        ("■ 5. Use of this software", [
            "By using this software, you are deemed to have read and accepted these notices.",
        ]),
    ],
}

STRINGS = {
    "ja": {
        "setup_title": "YDL セットアップ",
        "p_agree": "同意", "p_options": "オプション",
        "p_location": "インストール先", "p_install": "インストール",
        "terms_title": "利用規約・注意事項",
        "terms_sub": "内容をお読みのうえ、同意する場合は「同意する」を押してください。",
        "opt_title": "オプションの選択",
        "opt_sub": "インストール時の追加設定を選んでください。",
        "opt_shortcut": "デスクトップにショートカットを作成する",
        "opt_launch": "完了したら YDL を起動する",
        "loc_title": "インストール先の選択",
        "loc_sub": "YDL をインストールするフォルダを選んでください。",
        "loc_note": "インストールにはビルドを行うため、数分かかります。",
        "change": "変更",
        "install_title": "インストール",
        "preparing": "準備しています…",
        "btn_disagree": "同意しない", "btn_agree": "同意する",
        "btn_back": "戻る", "btn_next": "次へ",
        "btn_install": "インストール", "btn_installing": "インストール中…",
        "btn_done": "完了", "btn_retry": "もう一度",
        "quit_title": "セットアップを終了",
        "quit_msg": "同意しない場合はインストールできません。\n終了しますか？",
        "launch_fail_title": "起動に失敗",
        "launch_fail_msg": "YDL を起動できませんでした:\n{err}",
        "closing_title": "インストール中です",
        "closing_msg": "インストールを中止して閉じますか？",
        "choose_dir_title": "インストール先のフォルダを選択",
        "step_fmt": "ステップ {n} / {total}  {text}",
        "s_python": "Python を確認しています",
        "s_pip": "必要なライブラリをインストールしています",
        "s_ydl": "YDL.exe をビルドしています（数分かかります）",
        "s_unins": "YDL-uninstaller.exe をビルドしています",
        "s_copy": "インストールしています",
        "python_not_found": "tkinter 付きの Python 3 が見つかりません。",
        "tcl_unknown": "（Tcl/Tk の場所を特定できませんでした。PyInstaller の自動検出に任せます）",
        "err_cancelled": "中止しました",
        "err_cmd": "コマンドが失敗しました（終了コード {code}）。ログを確認してください。",
        "err_mkdir": "インストール先を作成できません: {err}\n「戻る」で別の場所（書き込めるフォルダ）を選んでください。",
        "err_noexe": "{name} が作成されませんでした。ログを確認してください。",
        "err_perm": "YDL が起動している可能性があります。YDL を終了してから、もう一度実行してください。",
        "copied": "コピーしました: {name}",
        "reg_ok": "「設定 > アプリ」に登録しました",
        "reg_fail": "（アプリ一覧への登録に失敗しました: {err}）",
        "sc_ok": "デスクトップにショートカットを作成しました",
        "sc_fail": "（ショートカットの作成に失敗しました: {err}）",
        "done_launch": "インストールが完了しました。「完了」を押すと YDL が起動します。",
        "done_close": "インストールが完了しました。「完了」を押して閉じてください。",
        "done_log": "完了: {exe}",
        "fail_status": "失敗しました: {message}",
        "fail_log": "失敗: {message}",
        "py_title": "Python が必要です",
        "py_msg": ("ビルドには Python 3 が必要です。\n\n"
                   "Python のダウンロードページを開きますか？\n\n"
                   "インストールのときは、次の2点に注意してください。\n"
                   "・「Add python.exe to PATH」にチェックを入れる\n"
                   "・「tcl/tk and IDLE」を外さない"),
    },
    "en": {
        "setup_title": "YDL Setup",
        "p_agree": "Agree", "p_options": "Options",
        "p_location": "Location", "p_install": "Install",
        "terms_title": "Terms of Use & Notices",
        "terms_sub": "Please read the following and click \"I Agree\" if you accept.",
        "opt_title": "Select Options",
        "opt_sub": "Choose additional settings for the installation.",
        "opt_shortcut": "Create a desktop shortcut",
        "opt_launch": "Launch YDL when finished",
        "loc_title": "Select Install Location",
        "loc_sub": "Choose the folder where YDL will be installed.",
        "loc_note": "Installation involves a build step and takes a few minutes.",
        "change": "Change",
        "install_title": "Install",
        "preparing": "Preparing…",
        "btn_disagree": "I Disagree", "btn_agree": "I Agree",
        "btn_back": "Back", "btn_next": "Next",
        "btn_install": "Install", "btn_installing": "Installing…",
        "btn_done": "Finish", "btn_retry": "Retry",
        "quit_title": "Exit Setup",
        "quit_msg": "YDL cannot be installed unless you agree.\nExit Setup?",
        "launch_fail_title": "Launch failed",
        "launch_fail_msg": "Could not launch YDL:\n{err}",
        "closing_title": "Installation in progress",
        "closing_msg": "Cancel the installation and close?",
        "choose_dir_title": "Select install folder",
        "step_fmt": "Step {n} / {total}  {text}",
        "s_python": "Checking Python",
        "s_pip": "Installing required libraries",
        "s_ydl": "Building YDL.exe (this takes a few minutes)",
        "s_unins": "Building YDL-uninstaller.exe",
        "s_copy": "Installing",
        "python_not_found": "Python 3 with tkinter was not found.",
        "tcl_unknown": "(Could not locate Tcl/Tk. Leaving it to PyInstaller's auto-detection.)",
        "err_cancelled": "Cancelled",
        "err_cmd": "Command failed (exit code {code}). Please check the log.",
        "err_mkdir": "Cannot create the install folder: {err}\nPress \"Back\" and choose another (writable) location.",
        "err_noexe": "{name} was not created. Please check the log.",
        "err_perm": "YDL may be running. Please close YDL and try again.",
        "copied": "Copied: {name}",
        "reg_ok": "Registered in Settings > Apps",
        "reg_fail": "(Failed to register in the apps list: {err})",
        "sc_ok": "Created a desktop shortcut",
        "sc_fail": "(Failed to create the shortcut: {err})",
        "done_launch": "Installation complete. Click \"Finish\" to launch YDL.",
        "done_close": "Installation complete. Click \"Finish\" to close.",
        "done_log": "Done: {exe}",
        "fail_status": "Failed: {message}",
        "fail_log": "Failed: {message}",
        "py_title": "Python is required",
        "py_msg": ("Python 3 is required to build YDL.\n\n"
                   "Open the Python download page?\n\n"
                   "When installing, please note the following:\n"
                   "- Check \"Add python.exe to PATH\"\n"
                   "- Do not uncheck \"tcl/tk and IDLE\""),
    },
}

tr = Translator(STRINGS)


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
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "YDL (YouTube Downloader)")
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
        self.title(tr("setup_title"))
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
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=PAD, pady=(22, 8))
        tk.Label(header, text=tr("setup_title"), font=(FONT, 16, "bold"),
                 bg=C["bg"], fg=C["text"], anchor="w").pack(side="left")
        self.lang_box = lang_switch(header, tr, FONT, C["bg"], C["text"], C["faint"],
                                    self.change_lang)

        self.steps_row = tk.Frame(self, bg=C["bg"])
        self.steps_row.pack(fill="x", padx=PAD)
        self.step_labels = []
        for i, key in enumerate(PAGE_KEYS):
            lbl = tk.Label(self.steps_row, text=f"{i + 1} {tr(key)}", font=(FONT, 9),
                           bg=C["bg"], fg=C["faint"])
            lbl.pack(side="left")
            self.step_labels.append(lbl)
            if i < len(PAGE_KEYS) - 1:
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

    def change_lang(self, code):
        if self.running or self.page == 3 or code == tr.lang:
            return
        tr.set(code)
        page = self.page
        for w in self.winfo_children():
            w.destroy()
        self.title(tr("setup_title"))
        self._build()
        self.show_page(page)

    def _page_terms(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, tr("terms_title"), tr("terms_sub"))

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
        for heading, lines in TERMS[tr.lang]:
            txt.insert("end", heading + "\n", "h")
            for line in lines:
                txt.insert("end", line + "\n")
        txt.config(state="disabled")
        return f

    def _page_options(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, tr("opt_title"), tr("opt_sub"))
        opts = tk.Frame(f, bg=C["bg"])
        opts.pack(fill="x", pady=(16, 0))
        self.chk_shortcut = self._check(opts, tr("opt_shortcut"), self.var_shortcut)
        self.chk_launch = self._check(opts, tr("opt_launch"), self.var_launch)
        return f

    def _page_location(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, tr("loc_title"), tr("loc_sub"))
        row = tk.Frame(f, bg=C["bg"])
        row.pack(fill="x", pady=(16, 0))
        self.path_label = tk.Label(row, text=self.install_dir, font=(FONT, 9), bg=C["panel"],
                                   fg=C["text"], anchor="w", wraplength=380, justify="left",
                                   padx=10, pady=8)
        self.path_label.pack(side="left", fill="x", expand=True)
        self.change_btn = tk.Button(row, text=tr("change"), font=(FONT, 9), relief="flat", bd=0,
                                    bg=C["panel"], fg=C["text"], activebackground=C["line"],
                                    activeforeground=C["text"], cursor="hand2", padx=14,
                                    command=self.choose_dir)
        self.change_btn.pack(side="right", fill="y", padx=(6, 0))
        tk.Label(f, text=tr("loc_note"), font=(FONT, 9), bg=C["bg"], fg=C["muted"],
                 anchor="w", wraplength=500, justify="left").pack(fill="x", pady=(12, 0))
        return f

    def _page_install(self):
        f = tk.Frame(self.body, bg=C["bg"])
        self._heading(f, tr("install_title"))
        self.bar = ttk.Progressbar(f, style="Setup.Horizontal.TProgressbar",
                                   maximum=100, mode="determinate")
        self.bar.pack(fill="x", pady=(14, 6))
        self.step_label = tk.Label(f, text=tr("preparing"), font=(FONT, 9),
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
        if n == 3:
            self.lang_box.pack_forget()
        else:
            self.lang_box.pack(side="right", anchor="s", pady=(0, 3))
        self.update_nav()

    def update_nav(self):
        p = self.page
        if p == 0:
            self._style_btn(self.back_btn, tr("btn_disagree"), True, False)
            self._style_btn(self.next_btn, tr("btn_agree"), True, True)
        elif p == 1:
            self._style_btn(self.back_btn, tr("btn_back"), True, False)
            self._style_btn(self.next_btn, tr("btn_next"), True, True)
        elif p == 2:
            self._style_btn(self.back_btn, tr("btn_back"), True, False)
            self._style_btn(self.next_btn, tr("btn_install"), True, True)
        else:
            if self.running:
                self._style_btn(self.back_btn, tr("btn_back"), False, False)
                self._style_btn(self.next_btn, tr("btn_installing"), False, True)
            elif self.done:
                self._style_btn(self.back_btn, tr("btn_back"), False, False)
                self._style_btn(self.next_btn, tr("btn_done"), True, True)
            else:
                self._style_btn(self.back_btn, tr("btn_back"), True, False)
                self._style_btn(self.next_btn, tr("btn_retry"), True, True)

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
                messagebox.showerror(tr("launch_fail_title"), tr("launch_fail_msg", err=e))
        self.destroy()

    def go_back(self):
        if self.running:
            return
        if self.page == 0:
            if messagebox.askyesno(tr("quit_title"), tr("quit_msg")):
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
            title=tr("choose_dir_title"),
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
        self.step_label.config(text=tr("preparing"), fg=C["muted"])
        self.bar.config(mode="indeterminate")
        self.bar.start(12)
        self.update_nav()

        options = dict(shortcut=self.var_shortcut.get(), launch=self.var_launch.get())
        threading.Thread(target=self.worker, args=(options,), daemon=True).start()

    def on_close(self):
        if self.running:
            if not messagebox.askyesno(tr("closing_title"), tr("closing_msg")):
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
            raise BuildError(tr("err_cancelled"))
        if code != 0:
            raise BuildError(tr("err_cmd", code=code))

    def worker(self, options):
        work = tempfile.mkdtemp(prefix="ydl_build_")
        self.work_dir = work
        try:

            self.step(1, tr("s_python"))
            py = find_python()
            if py is None:
                raise PythonMissing(tr("python_not_found"))
            self.log("Python: " + " ".join(py))

            self.step(2, tr("s_pip"))
            self.run(py + ["-m", "pip", "install", "-U", "--disable-pip-version-check",
                           "--progress-bar", "off", "yt-dlp", "imageio-ffmpeg", "pyinstaller"],
                     work)

            src = os.path.join(work, "src")
            os.makedirs(src, exist_ok=True)
            for name in ("main.py", "uninstall.py", "i18n.py", "icon.ico"):
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
                self.log(tr("tcl_unknown"))

            self.step(3, tr("s_ydl"))
            self.run(py + common + ["--name", "YDL", "--add-data", f"{ico};.",
                                    "--hidden-import=yt_dlp", "--collect-all", "imageio_ffmpeg"]
                     + tcl_extra + [os.path.join(src, "main.py")], work)

            self.step(4, tr("s_unins"))
            self.run(py + common + ["--name", "YDL-uninstaller",
                                    os.path.join(src, "uninstall.py")], work)

            self.step(5, tr("s_copy"))
            try:
                os.makedirs(self.install_dir, exist_ok=True)
            except OSError as e:
                raise BuildError(tr("err_mkdir", err=e))
            for name in ("YDL.exe", "YDL-uninstaller.exe"):
                exe_src = os.path.join(dist, name)
                if not os.path.exists(exe_src):
                    raise BuildError(tr("err_noexe", name=name))
                try:
                    shutil.copy2(exe_src, os.path.join(self.install_dir, name))
                except PermissionError:
                    raise BuildError(tr("err_perm"))
                self.log(tr("copied", name=name))

            try:
                register_uninstall(self.install_dir)
                self.log(tr("reg_ok"))
            except Exception as e:
                self.log(tr("reg_fail", err=e))

            exe = os.path.join(self.install_dir, "YDL.exe")
            if options["shortcut"]:
                try:
                    create_desktop_shortcut(exe)
                    self.log(tr("sc_ok"))
                except Exception as e:
                    self.log(tr("sc_fail", err=e))

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
                        text=tr("step_fmt", n=ev[1], total=TOTAL_STEPS, text=ev[2]),
                        fg=C["muted"])
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
        msg = tr("done_launch") if launch else tr("done_close")
        self.step_label.config(text=msg, fg=C["accent"])
        self.append_log(tr("done_log", exe=exe))
        self.update_nav()

    def on_error(self, message, python_missing):
        self.finish_progress()
        self.bar["value"] = 0
        self.step_label.config(text=tr("fail_status", message=message), fg=C["error"])
        self.append_log(tr("fail_log", message=message))
        self.update_nav()

        if python_missing:
            if messagebox.askyesno(tr("py_title"), tr("py_msg")):
                webbrowser.open("https://www.python.org/downloads/")

if __name__ == "__main__":
    Installer().mainloop()