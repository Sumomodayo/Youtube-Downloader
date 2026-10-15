import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\YDL"
NO_WINDOW = 0x08000000
NEW_GROUP = 0x00000200
BREAKAWAY = 0x01000000
TITLE = "YDL アンインストール"

def desktop_dir():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW, timeout=30)
    path = r.stdout.strip()
    return path or os.path.join(os.path.expanduser("~"), "Desktop")


def schedule_delete(install_dir):
    exe = os.path.join(install_dir, "YDL.exe")
    me = os.path.join(install_dir, "YDL-uninstaller.exe")

    if os.path.basename(install_dir).lower() == "ydl":
        remove = f'rmdir /s /q "{install_dir}" 2>nul'
    else:
        remove = f'del /f /q "{exe}" "{me}" 2>nul & rmdir "{install_dir}" 2>nul'

    inner = (f'taskkill /f /im YDL.exe >nul 2>nul & '
             f'for /l %i in (1,1,10) do @if exist "{me}" '
             f'(ping 127.0.0.1 -n 2 >nul & {remove})')
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    command = f'"{comspec}" /s /c "{inner}"'

    flags = NO_WINDOW | NEW_GROUP
    for extra in (BREAKAWAY, 0):
        try:
            subprocess.Popen(command, creationflags=flags | extra, close_fds=True,
                             cwd=tempfile.gettempdir(),
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue


def main():
    root = tk.Tk()
    root.withdraw()

    install_dir = os.path.dirname(os.path.abspath(sys.executable))

    if not messagebox.askyesno(
            TITLE,
            "YDL をこのパソコンから削除しますか？\n\n"
            f"削除する場所:\n{install_dir}\n\n"
            "YDL フォルダごと削除されます（YDL.exe と YDL-uninstaller.exe）。\n"
            "ダウンロードしたファイル（デスクトップの YDL フォルダなど）は削除されません。"):
        return

    try:
        lnk = os.path.join(desktop_dir(), "YDL.lnk")
        if os.path.exists(lnk):
            os.remove(lnk)
    except Exception:
        pass

    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
    except Exception:
        pass

    schedule_delete(install_dir)
    messagebox.showinfo(TITLE, "アンインストールが完了しました。")

if __name__ == "__main__":
    main()