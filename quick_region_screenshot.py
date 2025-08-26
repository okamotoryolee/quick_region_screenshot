# quick_region_screenshot.py  — Win32 RegisterHotKey 安定版
import os, sys, time, datetime, threading, tkinter as tk
from PIL import Image
import mss                    # pip install mss
# クリップボード（任意）
ENABLE_CLIPBOARD_COPY = True  # 必要なければ False
_clipboard_ok = False
if ENABLE_CLIPBOARD_COPY:
    try:
        import win32clipboard, win32con
        from io import BytesIO
        _clipboard_ok = True
    except Exception:
        _clipboard_ok = False

# ====== 設定 ======
SAVE_DIR_BASE = os.path.join(os.path.expanduser("~"), "Pictures", "QuickShots")
USE_DATE_SUBFOLDER = True
OPEN_FOLDER_AFTER_SAVE = True
OPEN_FILE_AFTER_SAVE   = False
FILENAME_PREFIX        = "snap"
SELECTION_ALPHA        = 0.20

# ホットキー設定（Win32仮想キー）
# Ctrl+Shift+A
HOTKEY_MOD_CTRL  = 0x0002
HOTKEY_MOD_SHIFT = 0x0004
VK_A             = 0x41
# 終了ホットキー Ctrl+Shift+Q
VK_Q             = 0x51
# ホットキーID（任意の整数）
HOTKEY_ID_CAPTURE = 1
HOTKEY_ID_QUIT    = 2
# ================

# ---- 便利関数 ----
def get_virtual_screen_geometry():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        w = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        h = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return x, y, w, h
    except Exception:
        root = tk.Tk(); root.withdraw()
        w = root.winfo_screenwidth(); h = root.winfo_screenheight()
        root.destroy()
        return 0, 0, w, h

def ensure_save_dir():
    base = SAVE_DIR_BASE
    if USE_DATE_SUBFOLDER:
        base = os.path.join(base, datetime.datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(base, exist_ok=True)
    return base

def open_path(path: str):
    try:
        os.startfile(path)
    except Exception as e:
        print(f"[WARN] パスを開けませんでした: {e}", flush=True)

def copy_image_to_clipboard(pil_img: Image.Image):
    if not _clipboard_ok:
        return
    try:
        with BytesIO() as output:
            pil_img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # BMPヘッダ(14byte)除去してDIB
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
        finally:
            win32clipboard.CloseClipboard()
        print("[INFO] クリップボードへコピー完了（Ctrl+Vで貼付可）", flush=True)
    except Exception as e:
        print(f"[WARN] クリップボードコピー失敗: {e}", flush=True)

def grab_region_mss(x1, y1, x2, y2) -> Image.Image:
    left, top = int(x1), int(y1)
    width, height = int(x2 - x1), int(y2 - y1)
    if width <= 0 or height <= 0:
        raise ValueError("Invalid capture size")
    with mss.mss() as sct:
        raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return Image.frombytes("RGB", raw.size, raw.rgb)

# ---- 範囲選択UI ----
class RegionSelector:
    def __init__(self):
        self.vx, self.vy, self.vw, self.vh = get_virtual_screen_geometry()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try: self.root.attributes("-alpha", SELECTION_ALPHA)
        except Exception: pass
        self.root.configure(bg="black")
        self.root.geometry(f"{self.vw}x{self.vh}+{self.vx}+{self.vy}")
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.start_x = self.start_y = 0
        self.rect = None
        self.root.bind("<Button-1>", self.on_mouse_down)
        self.root.bind("<B1-Motion>", self.on_mouse_drag)
        self.root.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.root.bind("<Escape>", self.on_escape)

    def on_escape(self, event=None): self.root.destroy()

    def on_mouse_down(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="white", width=2
        )

    def on_mouse_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        end_x, end_y = event.x, event.y
        x1 = self.vx + min(self.start_x, end_x)
        y1 = self.vy + min(self.start_y, end_y)
        x2 = self.vx + max(self.start_x, end_x)
        y2 = self.vy + max(self.start_y, end_y)
        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            self.root.destroy(); return

        self.root.withdraw(); self.root.update_idletasks()
        time.sleep(0.03)

        try:
            img = grab_region_mss(x1, y1, x2, y2)
        except Exception as e:
            print(f"[ERROR] キャプチャ失敗: {e}", flush=True)
            self.root.destroy(); return

        save_dir = ensure_save_dir()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(save_dir, f"{FILENAME_PREFIX}_{ts}.png")
        try:
            img.save(path)
            print(f"[INFO] Saved: {path}", flush=True)
        except Exception as e:
            print(f"[ERROR] 保存に失敗: {e}", flush=True)

        if ENABLE_CLIPBOARD_COPY:
            copy_image_to_clipboard(img)

        if OPEN_FILE_AFTER_SAVE:
            open_path(path)
        elif OPEN_FOLDER_AFTER_SAVE:
            open_path(save_dir)

        self.root.destroy()

    def run(self): self.root.mainloop()

def take_region_screenshot():
    RegionSelector().run()

# ---- Win32ホットキー待受け ----
def start_hotkey_loop():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # RegisterHotKey(NULL, id, modifiers, vk)
    if not user32.RegisterHotKey(None, HOTKEY_ID_CAPTURE, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_A):
        print("[ERROR] RegisterHotKey 失敗（Capture）", flush=True)
    if not user32.RegisterHotKey(None, HOTKEY_ID_QUIT, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_Q):
        print("[WARN] RegisterHotKey 失敗（Quit）", flush=True)

    print("[QuickShot] 起動しました。以下のホットキーで待受けします。", flush=True)
    print("[QuickShot] Ctrl+Shift+A : 範囲指定スクショ", flush=True)
    print("[QuickShot] Ctrl+Shift+Q : 終了", flush=True)
    print(f"[QuickShot] 保存先ベース: {SAVE_DIR_BASE}", flush=True)
    if USE_DATE_SUBFOLDER: print("[QuickShot] 日付サブフォルダ: 有効", flush=True)
    if OPEN_FILE_AFTER_SAVE: print("[QuickShot] 保存後: ファイルを開く", flush=True)
    elif OPEN_FOLDER_AFTER_SAVE: print("[QuickShot] 保存後: フォルダを開く", flush=True)
    if ENABLE_CLIPBOARD_COPY:
        print(f"[QuickShot] クリップボード: {'有効' if _clipboard_ok else 'pywin32未検出→無効'}", flush=True)

    # メッセージループ
    WM_HOTKEY = 0x0312

    class MSG(ctypes.Structure):
        _fields_ = [("hwnd",    wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam",  wintypes.WPARAM),
                    ("lParam",  wintypes.LPARAM),
                    ("time",    wintypes.DWORD),
                    ("pt",      wintypes.POINT)]

    msg = MSG()
    try:
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0:  # WM_QUIT
                break
            if ret == -1:
                # 取得失敗時は少し待って続行（まれ）
                time.sleep(0.01)
                continue

            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                if hotkey_id == HOTKEY_ID_CAPTURE:
                    threading.Thread(target=take_region_screenshot, daemon=True).start()
                elif hotkey_id == HOTKEY_ID_QUIT:
                    print("[QuickShot] 終了ホットキー", flush=True)
                    break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID_CAPTURE)
        user32.UnregisterHotKey(None, HOTKEY_ID_QUIT)

if __name__ == "__main__":
    print("[QuickShot] booting...", flush=True)
    try:
        # メインスレッドでメッセージループを回す（安定のため）
        start_hotkey_loop()
    finally:
        print("[QuickShot] exit.", flush=True)
