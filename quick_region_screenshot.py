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
SAVE_FORMAT            = "WEBP"  # "PNG", "JPEG", "WEBP"
IMAGE_QUALITY          = 80      # 1-100 (used for JPEG and WEBP)
TOAST_DURATION_MS      = 4500   # トースト表示時間(ms)

# ホットキー設定（Win32仮想キー）
# Ctrl+Shift+A
HOTKEY_MOD_CTRL  = 0x0002
HOTKEY_MOD_SHIFT = 0x0004
# Ctrl+Shift+S (Fullscreen)
VK_S             = 0x53
# Ctrl+Shift+Z (Pin)
VK_Z             = 0x5A
# 終了ホットキー Ctrl+Shift+Q
VK_Q             = 0x51
# ホットキーID（任意の整数）
HOTKEY_ID_CAPTURE    = 1
HOTKEY_ID_QUIT       = 2
HOTKEY_ID_FULLSCREEN = 3
HOTKEY_ID_PIN        = 4
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

# ---- トースト通知 ----
def show_toast(message: str, save_dir: str = None):
    """完全独立スレッド・独自Tkルートで表示するトースト通知。
    どのコンテキストから呼んでも安全（Toplevelpではなく Tk を使う）。"""
    def _run():
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            try:
                root.attributes("-alpha", 0.93)
            except Exception:
                pass

            BG     = "#1e1e2e"
            FG     = "#cdd6f4"
            ACCENT = "#89b4fa"

            frame = tk.Frame(root, bg=BG, padx=16, pady=12)
            frame.pack(fill=tk.BOTH, expand=True)

            tk.Label(frame, text="\U0001f4f8  " + message,
                     bg=BG, fg=FG, font=("Segoe UI", 10), anchor="w").pack(fill=tk.X)

            if save_dir:
                def _open_folder(e=None):
                    open_path(save_dir)
                    root.destroy()

                hint = tk.Label(frame, text="\u30af\u30ea\u30c3\u30af\u3067\u30d5\u30a9\u30eb\u30c0\u3092\u958b\u304f",
                                bg=BG, fg=ACCENT, font=("Segoe UI", 8),
                                cursor="hand2", anchor="w")
                hint.pack(fill=tk.X, pady=(3, 0))
                hint.bind("<Button-1>", _open_folder)
                root.bind("<Button-1>", _open_folder)

            # 位置: 画面右下（タスクバー上）
            root.update_idletasks()
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            w  = root.winfo_reqwidth()
            h  = root.winfo_reqheight()
            margin = 16
            root.geometry(f"{w}x{h}+{sw - w - margin}+{sh - h - margin - 48}")

            root.after(TOAST_DURATION_MS, root.destroy)
            root.mainloop()
        except Exception as e:
            print(f"[WARN] \u30c8\u30fc\u30b9\u30c8\u8868\u793a\u5931\u6557: {e}", flush=True)

    threading.Thread(target=_run, daemon=True).start()

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
        ext = SAVE_FORMAT.lower()
        if ext not in ["png", "jpeg", "jpg", "webp"]:
            ext = "png"
        if ext == "jpg": ext = "jpeg"

        path = os.path.join(save_dir, f"{FILENAME_PREFIX}_{ts}.{ext}")
        try:
            if ext in ["jpeg", "webp"]:
                img.save(path, format=ext.upper(), quality=IMAGE_QUALITY)
            else:
                img.save(path, format=ext.upper())
            print(f"[INFO] Saved: {path}", flush=True)
        except Exception as e:
            print(f"[ERROR] 保存に失敗: {e}", flush=True)

        if ENABLE_CLIPBOARD_COPY:
            copy_image_to_clipboard(img)

        show_toast("保存完了", save_dir)

        if OPEN_FILE_AFTER_SAVE:
            open_path(path)

        self.root.destroy()

    def run(self): self.root.mainloop()

def take_region_screenshot():
    RegionSelector().run()

# ---- ピン留めUI ----
class PinnedImageWindow:
    def __init__(self, pil_img: Image.Image, x: int, y: int):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        from PIL import ImageTk
        self.photo = ImageTk.PhotoImage(pil_img)
        
        width = pil_img.width
        height = pil_img.height
        
        # 画面外にはみ出さないように初期位置を調整（簡易的）
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        pos_x = min(max(0, x), screen_w - width)
        pos_y = min(max(0, y), screen_h - height)
        
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        
        self.label = tk.Label(self.root, image=self.photo, bd=2, relief="solid", bg="gray")
        self.label.pack(fill=tk.BOTH, expand=True)
        
        # ドラッグ移動用のイベントバインド
        self.label.bind("<Button-1>", self.on_drag_start)
        self.label.bind("<B1-Motion>", self.on_drag_motion)
        
        # 閉じる操作（右クリック または ダブルクリック または Esc）
        self.label.bind("<Button-3>", self.close)
        self.label.bind("<Double-Button-1>", self.close)
        self.root.bind("<Escape>", self.close)
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    def on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def on_drag_motion(self, event):
        x = self.root.winfo_x() - self._drag_start_x + event.x
        y = self.root.winfo_y() - self._drag_start_y + event.y
        self.root.geometry(f"+{x}+{y}")

    def close(self, event=None):
        self.root.destroy()

class PinRegionSelector(RegionSelector):
    # 既存のリージョンセレクタを継承し、mouseupの挙動だけオーバライドする
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

        # クリップボードには入れる（便利なので）
        if ENABLE_CLIPBOARD_COPY:
            copy_image_to_clipboard(img)

        print("[INFO] Pinned region.", flush=True)
        
        # ピン留めウィンドウを生成して表示（親プロセスに依存するためメインループを共有させる工夫が必要）
        # rootはwithdrawしているがmainloopは継続中。なので別のToplevelを作って管理する。
        PinnedImageWindow(img, x1, y1)
        
        # ※ 注意：親のself.rootをdestroyするとToplevelも消えてしまうので、
        # ピン留め用は self.root を withdraw したまま生かしておく。
        # アプリ終了時に一括で消える。

def take_pin_screenshot():
    PinRegionSelector().run()

# ---- モニター選択UI ----
class FullScreenSelector:
    def __init__(self, monitors):
        self.monitors = monitors # mss monitors list
        self.vx, self.vy, self.vw, self.vh = get_virtual_screen_geometry()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try: self.root.attributes("-alpha", 0.05) # ほぼ透明
        except Exception: pass
        self.root.configure(bg="black")
        self.root.geometry(f"{self.vw}x{self.vh}+{self.vx}+{self.vy}")
        
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 各モニタの領域に枠と文字を表示
        # ctypes monitors list start from 0, and has no 'all' combined monitor.
        for i, m in enumerate(self.monitors, start=1):
            # 仮想スクリーン座標系での位置
            mx, my, mw, mh = m['left'], m['top'], m['width'], m['height']
            # キャンバス上の座標に変換（self.vx, self.vyを引く）
            cx, cy = mx - self.vx, my - self.vy
            
            # 枠を描画
            self.canvas.create_rectangle(cx, cy, cx+mw, cy+mh, outline="cyan", width=5)
            # 中央に文字
            self.canvas.create_text(cx+mw/2, cy+mh/2, text=f"Monitor {i}\nClick to Capture", fill="cyan", font=("Arial", 30, "bold"))
            # 透明な四角を置いてクリック判定用にする
            btn_id = self.canvas.create_rectangle(cx, cy, cx+mw, cy+mh, fill="black", stipple="gray12", outline="") 
            self.canvas.tag_bind(btn_id, "<Button-1>", lambda e, mon=m: self.on_monitor_click(mon))
            self.canvas.tag_bind(btn_id, "<Enter>", lambda e, item_id=btn_id: self.canvas.itemconfig(item_id, stipple="gray50"))
            self.canvas.tag_bind(btn_id, "<Leave>", lambda e, item_id=btn_id: self.canvas.itemconfig(item_id, stipple="gray12"))

        self.root.bind("<Escape>", self.on_escape)
        self._selected_monitor = None
    
    def on_escape(self, event=None):
        self._selected_monitor = None
        self.root.quit()

    def on_monitor_click(self, monitor_geo):
        self._selected_monitor = monitor_geo
        self.root.quit()  # mainloopを抜けるだけ。destroyはしない

    def run(self):
        self.root.mainloop()
        # mainloopが終わったらウィンドウを非表示にしてからキャプチャ
        try:
            self.root.withdraw()
            self.root.update_idletasks()
        except Exception:
            pass
        time.sleep(0.1)
        try:
            self.root.destroy()
        except Exception:
            pass
        # キャプチャ実行
        if self._selected_monitor:
            m = self._selected_monitor
            do_fullscreen_capture(m['left'], m['top'], m['width'], m['height'])

def do_fullscreen_capture(x, y, w, h):
    try:
        img = grab_region_mss(x, y, x + w, y + h)
    except Exception as e:
        print(f"[ERROR] キャプチャ失敗: {e}", flush=True)
        return

    save_dir = ensure_save_dir()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ext = SAVE_FORMAT.lower()
    if ext not in ["png", "jpeg", "jpg", "webp"]:
        ext = "png"
    if ext == "jpg": ext = "jpeg"

    path = os.path.join(save_dir, f"{FILENAME_PREFIX}_full_{ts}.{ext}")
    try:
        if ext in ["jpeg", "webp"]:
            img.save(path, format=ext.upper(), quality=IMAGE_QUALITY)
        else:
            img.save(path, format=ext.upper())
        print(f"[INFO] Saved: {path}", flush=True)
    except Exception as e:
        print(f"[ERROR] 保存に失敗: {e}", flush=True)

    if ENABLE_CLIPBOARD_COPY:
        copy_image_to_clipboard(img)

    show_toast("保存完了", save_dir)

    if OPEN_FILE_AFTER_SAVE:
        open_path(path)

# ---- モニター列挙 (ctypes) ----
def get_monitors_ctypes():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    
    monitors = []
    
    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        monitors.append({
            'left': r.left,
            'top': r.top,
            'width': r.right - r.left,
            'height': r.bottom - r.top,
            'handle': hMonitor
        })
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(monitor_enum_proc), 0)
    
    # Sort by position (optional, but good for consistent numbering)
    monitors.sort(key=lambda m: (m['left'], m['top']))
    return monitors

def take_fullscreen_screenshot():
    # mssを使わずctypesでモニター情報を取得
    monitors = get_monitors_ctypes()
    
    if not monitors:
        print("[ERROR] モニターが検出されませんでした", flush=True)
        return

    if len(monitors) == 1:
        # Single monitor
        m = monitors[0]
        do_fullscreen_capture(m['left'], m['top'], m['width'], m['height'])
    else:
        # Multi monitor
        FullScreenSelector(monitors).run()

# ---- Win32ホットキー待受け ----
def start_hotkey_loop():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Constants
    HOTKEY_ID_CAPTURE    = 1
    HOTKEY_ID_QUIT       = 2
    HOTKEY_ID_FULLSCREEN = 3
    
    HOTKEY_MOD_CTRL  = 0x0002
    HOTKEY_MOD_SHIFT = 0x0004
    VK_A = 0x41
    VK_Q = 0x51
    VK_S = 0x53 # 'S' key
    VK_Z = 0x5A # 'Z' key

    # RegisterHotKey(NULL, id, modifiers, vk)
    if not user32.RegisterHotKey(None, HOTKEY_ID_CAPTURE, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_A):
        print("[ERROR] RegisterHotKey 失敗（Capture）", flush=True)
    if not user32.RegisterHotKey(None, HOTKEY_ID_QUIT, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_Q):
        print("[WARN] RegisterHotKey 失敗（Quit）", flush=True)
    if not user32.RegisterHotKey(None, HOTKEY_ID_FULLSCREEN, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_S):
        print("[WARN] RegisterHotKey 失敗（Fullscreen）", flush=True)
    if not user32.RegisterHotKey(None, HOTKEY_ID_PIN, HOTKEY_MOD_CTRL | HOTKEY_MOD_SHIFT, VK_Z):
        print("[WARN] RegisterHotKey 失敗（Pin）", flush=True)

    print("[QuickShot] 起動しました。以下のホットキーで待受けします。", flush=True)
    print("[QuickShot] Ctrl+Shift+A : 範囲指定スクショ", flush=True)
    print("[QuickShot] Ctrl+Shift+S : 画面全体スクショ（マルチモニタ対応）", flush=True)
    print("[QuickShot] Ctrl+Shift+Z : 範囲指定でピン留め（最前面表示）", flush=True)
    print("[QuickShot] Ctrl+Shift+Q : 終了", flush=True)
    print(f"[QuickShot] 保存先ベース: {SAVE_DIR_BASE}", flush=True)
    print(f"[QuickShot] 保存フォーマット: {SAVE_FORMAT} (Quality: {IMAGE_QUALITY})", flush=True)
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
                elif hotkey_id == HOTKEY_ID_FULLSCREEN:
                    threading.Thread(target=take_fullscreen_screenshot, daemon=True).start()
                elif hotkey_id == HOTKEY_ID_PIN:
                    threading.Thread(target=take_pin_screenshot, daemon=True).start()
                elif hotkey_id == HOTKEY_ID_QUIT:
                    print("[QuickShot] 終了ホットキー", flush=True)
                    break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID_CAPTURE)
        user32.UnregisterHotKey(None, HOTKEY_ID_QUIT)
        user32.UnregisterHotKey(None, HOTKEY_ID_FULLSCREEN)
        user32.UnregisterHotKey(None, HOTKEY_ID_PIN)

if __name__ == "__main__":
    print("[QuickShot] booting...", flush=True)
    try:
        # メインスレッドでメッセージループを回す（安定のため）
        start_hotkey_loop()
    finally:
        print("[QuickShot] exit.", flush=True)

