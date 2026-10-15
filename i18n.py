import json
import os

LANGS = {"ja": "日本語", "en": "English"}
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "YDL")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def _system_lang() -> str:
    try:
        import ctypes
        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return "ja" if primary == 0x11 else "en"
    except Exception:
        return "ja"


def load_lang() -> str:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lang = json.load(f).get("lang")
        if lang in LANGS:
            return lang
    except (OSError, ValueError, AttributeError):
        pass
    return _system_lang()


def save_lang(lang: str):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
    except OSError:
        pass


class Translator:

    def __init__(self, table: dict):
        self.table = table
        self.lang = load_lang()

    def __call__(self, key: str, **kw) -> str:
        s = self.table.get(self.lang, {}).get(key)
        if s is None:
            s = self.table["ja"].get(key, key)
        return s.format(**kw) if kw else s

    def set(self, lang: str):
        if lang in LANGS:
            self.lang = lang
            save_lang(lang)


def lang_switch(parent, tr, font, bg, fg_on, fg_off, on_change):
    import tkinter as tk
    f = tk.Frame(parent, bg=bg)
    for i, (code, name) in enumerate(LANGS.items()):
        if i:
            tk.Label(f, text="|", font=(font, 9), bg=bg, fg=fg_off).pack(side="left", padx=5)
        on = tr.lang == code
        lb = tk.Label(f, text=name, font=(font, 9, "bold" if on else "normal"),
                      bg=bg, fg=fg_on if on else fg_off,
                      cursor="arrow" if on else "hand2")
        lb.pack(side="left")
        if not on:
            lb.bind("<Button-1>", lambda e, c=code: on_change(c))
    return f