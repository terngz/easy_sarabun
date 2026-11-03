"""Easy Sarabun - เครื่องมือแปลงเลขไทย/อารบิก (Keep Format)"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import font as tkfont

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

try:
    import winsound
except ImportError:  # ไม่ใช่ Windows
    winsound = None

try:
    import pythoncom
    import win32api
    import win32clipboard
    import win32com.client
    import win32con
    import win32gui
    import win32process

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from clip_format import convert_payload
from engine import get_converter
from file_handler import FILETYPES, SUPPORTED, process_file
from hotkey import HotkeyManager, combo_from_tk_event, format_combo
import updater

# ───────────────────────── Constants ─────────────────────────
APP_NAME = "Easy Sarabun"
APP_VERSION = "1.0.0"
COPYRIGHT = "© 2026 Konnext Group, All Rights Reserved."
RIGHTS = "Free to Use"
GITHUB_URL = "https://github.com/terngz/easy_sarabun"
KOFI_URL = "https://ko-fi.com/Y8I2292JV2"
DEFAULT_HOTKEY = "ctrl+shift+t"
CONFIG_PATH = Path(os.getenv("APPDATA", Path.home())) / "EasySarabun" / "config.json"

# (light, dark)
ACCENT = ("#2f6f62", "#4a9a8a")
ACCENT_HOVER = ("#265a50", "#3d8374")
SURFACE = ("#f5f5f3", "#262626")
BORDER = ("#dcdcd8", "#3b3b3b")
MUTED = ("#77756f", "#9b9993")
TEXT = ("#1f1f1f", "#ececec")
OK = ("#2f7d4f", "#5fbf86")
ERR = ("#c0392b", "#e67e73")
KOFI_COLOR = "#78756c"
KOFI_HOVER = "#66635b"

SRC_ARABIC, SRC_THAI = "0123456789", "๐๑๒๓๔๕๖๗๘๙"
VK_C, VK_V = 0x43, 0x56
IGNORE_CLASSES = {"Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW"}


# ───────────────────────── Config / Fonts ─────────────────────────
def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def register_fonts() -> None:
    """โหลดฟอนต์ Mitr จาก assets/fonts เข้าโปรเซสนี้ (ไม่ต้องติดตั้งลงเครื่อง)"""
    if os.name != "nt":
        return
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "fonts"
    for f in base.glob("*.ttf"):
        ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)  # FR_PRIVATE


def resource_path(*parts: str) -> Path:
    """คืน path ไปยังไฟล์ที่ฝังในแพ็กเกจ PyInstaller หรือแหล่งรัน (ไดเรกทอรีนี้)"""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / Path(*parts)


# ───────────────────────── System helpers ─────────────────────────
def beep(freq: int = 1000, ms: int = 100) -> None:
    if winsound:
        threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()


def _key(vk: int, up: bool = False) -> None:
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP if up else 0, 0)


def send_ctrl(vk: int) -> None:
    if not HAS_WIN32:
        return
    _key(win32con.VK_CONTROL)
    _key(vk)
    time.sleep(0.03)
    _key(vk, True)
    _key(win32con.VK_CONTROL, True)


def wait_keys_released(timeout: float = 1.5) -> None:
    """รอให้ผู้ใช้ปล่อย Ctrl/Shift/Alt จากคีย์ลัดก่อน ไม่งั้น Ctrl+C จะกลายเป็น Ctrl+Shift+C ฯลฯ"""
    if not HAS_WIN32:
        return
    vks = (win32con.VK_CONTROL, win32con.VK_SHIFT, win32con.VK_MENU)
    end = time.time() + timeout
    while time.time() < end and any(win32api.GetAsyncKeyState(vk) & 0x8000 for vk in vks):
        time.sleep(0.02)
    for vk in vks:  # ถ้ายังค้างอยู่ ปล่อยให้เอง
        if win32api.GetAsyncKeyState(vk) & 0x8000:
            _key(vk, True)
    time.sleep(0.03)


def focus_window(hwnd: int) -> bool:
    """นำหน้าต่างปลายทางกลับมา foreground (แทนการจำลอง Alt+Tab ที่ Windows มักไม่ยอมรับ)"""
    if not HAS_WIN32:
        return True
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    for _ in range(20):
        if win32gui.GetForegroundWindow() == hwnd:
            time.sleep(0.12)
            return True
        time.sleep(0.03)
    return False


# ── Clipboard (text + HTML + RTF) ──
def _fmt(name: str) -> int:
    return win32clipboard.RegisterClipboardFormat(name)


def _clipboard_retry(action, attempts: int = 10):
    for _ in range(attempts):
        try:
            win32clipboard.OpenClipboard()
            try:
                return action()
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            time.sleep(0.03)
    return None


def get_clipboard_payload() -> dict:
    """อ่านทุกฟอร์แมตข้อความ: text / html / rtf"""
    if not HAS_WIN32:
        import pyperclip
        return {"text": pyperclip.paste()}

    def read():
        out = {}
        for key, fmt in (
            ("text", win32clipboard.CF_UNICODETEXT),
            ("html", _fmt("HTML Format")),
            ("rtf", _fmt("Rich Text Format")),
        ):
            if win32clipboard.IsClipboardFormatAvailable(fmt):
                out[key] = win32clipboard.GetClipboardData(fmt)
        return out

    return _clipboard_retry(read) or {}


def set_clipboard_payload(payload: dict) -> None:
    """เขียนกลับทุกฟอร์แมตพร้อมกัน → วางแบบ Keep Source Formatting ได้"""
    if not HAS_WIN32:
        import pyperclip
        pyperclip.copy(payload.get("text", ""))
        return

    def write():
        win32clipboard.EmptyClipboard()
        if "text" in payload:
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, payload["text"])
        if "html" in payload:
            win32clipboard.SetClipboardData(_fmt("HTML Format"), payload["html"] + b"\x00")
        if "rtf" in payload:
            win32clipboard.SetClipboardData(_fmt("Rich Text Format"), payload["rtf"] + b"\x00")

    _clipboard_retry(write)


def copy_selection() -> dict:
    """Ctrl+C แล้วรอข้อมูลใหม่ (เคลียร์คลิปบอร์ดก่อน กันดึงของเก่ามาแปลงผิด)"""
    if HAS_WIN32:
        _clipboard_retry(win32clipboard.EmptyClipboard)
    send_ctrl(VK_C)
    for _ in range(20):
        time.sleep(0.04)
        payload = get_clipboard_payload()
        if payload.get("text"):
            return payload
    return {}


def replace_in_word_selection(reverse: bool) -> bool:
    """แปลงข้อความที่ไฮไลต์ใน MS Word ผ่าน COM (Keep Format 100%)
    ทำงานเฉพาะเมื่อหน้าต่างที่ active คือ Word เท่านั้น"""
    if not HAS_WIN32:
        return False
    try:
        if win32gui.GetClassName(win32gui.GetForegroundWindow()) != "OpusApp":
            return False
    except Exception:
        return False

    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.GetActiveObject("Word.Application")
        selection = app.Selection
        text = selection.Text if selection else ""
        if not text or not text.strip():
            return False

        src, dst = (SRC_THAI, SRC_ARABIC) if reverse else (SRC_ARABIC, SRC_THAI)
        trans = dict(zip(src, dst))

        # แทนที่ตัวเลขทีละตัวอักษรด้วย Range.Text บนช่วง 1 ตัวอักษร
        # Word จะให้ข้อความใหม่รับฟอร์แมตของตัวอักษรตัวแรกใน range นั้น
        # (สี ขนาด ตัวหนา/เอียง ฯลฯ) -> Replace แล้วฟอร์แมตไม่เพี้ยน
        # ต่างจาก Find/Replace ที่อาจรีเซ็ตฟอร์แมตของตัวเลขที่แทนที่
        start, end = selection.Start, selection.End
        pos = start
        while pos < end:
            r = app.Range(pos, pos + 1)
            if r.Text in trans:
                r.Text = trans[r.Text]
            pos += 1
        return True
    except Exception:
        return False
    finally:
        pythoncom.CoUninitialize()


# ───────────────────────── About dialog ─────────────────────────
class AboutDialog(ctk.CTkToplevel):
    def __init__(self, app: "EasySarabunApp"):
        super().__init__(app)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.transient(app)
        self.attributes("-topmost", True)

        w, h = 360, 440
        x = app.winfo_x() + (app.winfo_width() - w) // 2
        y = app.winfo_y() + (app.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

        f = app.font
        ctk.CTkLabel(self, text=APP_NAME, font=f(26, True), text_color=ACCENT).pack(pady=(30, 0))
        ctk.CTkLabel(self, text=f"เวอร์ชัน {APP_VERSION}", font=f(12), text_color=MUTED).pack(pady=(2, 14))

        ctk.CTkLabel(
            self,
            text=(
                "แปลงตัวเลขอารบิก (0-9) เป็นเลขไทย (๐-๙) และกลับกัน\n"
                "ใช้ได้กับไฟล์ Word, คลิปบอร์ด และข้อความที่ไฮไลต์\n"
                "โดยคงรูปแบบเดิมไว้ทั้งหมด\n(เฉพาะการลากไฟล์วางแปลงทั้งไฟล์)\n"
            ),
            font=f(13), text_color=TEXT, justify="center",
        ).pack(padx=24)


        ctk.CTkButton(
            self, text="☕  เลี้ยงกาแฟผมได้", height=42, corner_radius=10, font=f(14, True),
            fg_color=KOFI_COLOR, hover_color=KOFI_HOVER, text_color="white",
            command=lambda: webbrowser.open(KOFI_URL),
        ).pack(fill="x", padx=40)

        # ctk.CTkButton(
        #     self, text="GitHub  ·  terngz/easy_sarabun", height=38, corner_radius=10, font=f(13),
        #     fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT,
        #     hover_color=SURFACE, command=lambda: webbrowser.open(GITHUB_URL),
        # ).pack(fill="x", padx=40, pady=(10, 0))
        
        ctk.CTkFrame(self, height=1, fg_color=BORDER).pack(fill="x", padx=40, pady=20)

        ctk.CTkLabel(self, text=COPYRIGHT, font=f(12), text_color=MUTED).pack()
        ctk.CTkLabel(self, text=RIGHTS, font=f(12), text_color=MUTED).pack(pady=(0, 20))

        self.after(60, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.focus()
        except Exception:
            pass


# ───────────────────────── Main app ─────────────────────────
class EasySarabunApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        families = set(tkfont.families(self))
        self.ff = "Mitr" if "Mitr" in families else "Tahoma"
        self.ff_med = "Mitr Medium" if "Mitr Medium" in families else self.ff

        self.config_data = load_config()
        self.hotkey = self.config_data.get("hotkey", DEFAULT_HOTKEY)
        self.reverse_mode = bool(self.config_data.get("reverse", False))  # True: ๐-๙ ➔ 0-9

        self.title(APP_NAME)
        self.geometry("420x580")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._set_app_icon()

        self._about: AboutDialog | None = None
        self._busy = threading.Lock()
        self._last_hwnd: int | None = None  # หน้าต่างล่าสุดที่ไม่ใช่โปรแกรมนี้
        self._recording = False
        self._update_checking = False

        self._build_ui()
        self._setup_dnd()

        self.hotkeys = HotkeyManager(lambda: self.convert_selection(None))
        if not self.hotkeys.register(self.hotkey):
            self.set_status(f"คีย์ลัด {format_combo(self.hotkey)} ถูกใช้โดยโปรแกรมอื่น", "err")

        self._track_foreground()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # ตรวจสอบอัปเดตอัตโนมัติหลัง UI ขึ้นแล้ว (ไม่บังคับ ไม่รบกวน)
        self.after(1500, self._check_update_bg)

    def _set_app_icon(self) -> None:
        """ตั้งไอคอนหน้าต่าง + ไอคอน Taskbar"""
        try:
            ico = resource_path("icon.ico")
            self.iconbitmap(str(ico))
        except Exception:
            pass
        if HAS_WIN32:
            try:  # AppUserModelID -> ให้ Taskbar แสดง icon เดียวของ app (ไม่ใช่ python.exe)
                win32com.client.Dispatch("Shell.Application")  # กัน COM init ภายหลัง
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Konnext.EasySarabun")
            except Exception:
                pass

    # ── fonts ──
    def font(self, size: int, bold: bool = False) -> ctk.CTkFont:
        if bold and self.ff_med != self.ff:
            return ctk.CTkFont(family=self.ff_med, size=size)
        return ctk.CTkFont(family=self.ff, size=size, weight="bold" if bold else "normal")

    # ── UI ──
    def _build_ui(self):
        pad = 28
        f = self.font

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=pad, pady=(20, 0))
        ctk.CTkLabel(header, text=APP_NAME, font=f(24, True), text_color=ACCENT).pack(side="left")
        self.btn_update = ctk.CTkButton(
            header, text="อัปเดต", width=66, height=28, corner_radius=14, font=f(12),
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=TEXT, hover_color=SURFACE, command=self.on_check_update,
        )
        self.btn_update.pack(side="right", padx=(6, 6))
        ctk.CTkButton(
            header, text="About", width=66, height=28, corner_radius=14, font=f(12),
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=TEXT, hover_color=SURFACE, command=self.open_about,
        ).pack(side="right")

        ctk.CTkLabel(
            self, text="แปลงเลขไทย ⇄ อารบิก โดยคงฟอร์แมตเดิม",
            font=f(12), text_color=MUTED, anchor="w",
        ).pack(fill="x", padx=pad, pady=(0, 14))

        # โหมดการแปลง
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=14)
        card.pack(fill="x", padx=pad)
        ctk.CTkLabel(card, text="โหมดการแปลง", font=f(11), text_color=MUTED).pack(pady=(12, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(pady=(0, 4))
        self.lbl_left = ctk.CTkLabel(row, text="อารบิก ➔ ไทย", width=110, anchor="e")
        self.lbl_left.pack(side="left")
        self.sw_mode = ctk.CTkSwitch(
            row, text="", width=56, switch_width=52, switch_height=26,
            fg_color=ACCENT, progress_color=ACCENT,
            button_color="white", button_hover_color="#f0f0f0",
            command=self.on_toggle_mode,
        )
        self.sw_mode.pack(side="left", padx=10)
        if self.reverse_mode:
            self.sw_mode.select()
        self.lbl_right = ctk.CTkLabel(row, text="ไทย ➔ อารบิก", width=110, anchor="w")
        self.lbl_right.pack(side="left")

        self.lbl_example = ctk.CTkLabel(card, text="", font=f(20, True), text_color=ACCENT)
        self.lbl_example.pack(pady=(2, 14))
        self._refresh_mode_ui()

        # ไฟล์เอกสาร (ทุกชนิดที่รองรับ)
        self.drop = ctk.CTkFrame(
            self, fg_color="transparent", border_width=1, border_color=BORDER, corner_radius=14
        )
        self.drop.pack(fill="x", padx=pad, pady=(14, 0))
        lbl1 = ctk.CTkLabel(self.drop, text="ลากไฟล์เอกสารมาวางที่นี่", font=f(14, True), text_color=TEXT)
        lbl1.pack(pady=(16, 0))
        lbl2 = ctk.CTkLabel(
            self.drop, text="Word · PowerPoint · Excel · ODF · RTF · TXT",
            font=f(11), text_color=MUTED,
        )
        lbl2.pack(pady=(0, 4))
        lbl3 = ctk.CTkLabel(self.drop, text="หรือคลิกเพื่อเลือกไฟล์ (ได้หลายไฟล์)", font=f(12), text_color=MUTED)
        lbl3.pack(pady=(0, 16))
        for w in (self.drop, lbl1, lbl2, lbl3):
            w.bind("<Button-1>", lambda _e: self.on_select_file())
            w.configure(cursor="hand2")

        # คลิปบอร์ด
        ctk.CTkButton(
            self, text="แปลงข้อความในคลิปบอร์ด", height=44, corner_radius=10, font=f(14, True),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white",
            command=self.on_convert_clipboard,
        ).pack(fill="x", padx=pad, pady=(14, 0))

        # ข้อความที่ไฮไลต์
        ctk.CTkButton(
            self, text="แปลงข้อความที่ไฮไลต์", height=44, corner_radius=10, font=f(14, True),
            fg_color="transparent", border_width=1, border_color=ACCENT, text_color=ACCENT,
            hover_color=SURFACE, command=self.on_convert_selection,
        ).pack(fill="x", padx=pad, pady=(10, 0))

        # คีย์ลัด (กดเพื่อเปลี่ยน)
        hk_row = ctk.CTkFrame(self, fg_color="transparent")
        hk_row.pack(pady=(12, 0))
        ctk.CTkLabel(hk_row, text="คีย์ลัด", font=f(12), text_color=MUTED).pack(side="left", padx=(0, 8))
        self.btn_hotkey = ctk.CTkButton(
            hk_row, text=format_combo(self.hotkey), width=150, height=28, corner_radius=14, font=f(12),
            fg_color=SURFACE, hover_color=BORDER, text_color=TEXT, command=self.start_recording,
        )
        self.btn_hotkey.pack(side="left")

        self.lbl_status = ctk.CTkLabel(self, text="พร้อมใช้งาน", font=f(11), text_color=MUTED)
        self.lbl_status.pack(side="bottom", pady=14)

    def _refresh_mode_ui(self):
        f, rev = self.font, self.reverse_mode
        self.lbl_left.configure(font=f(13, not rev), text_color=MUTED if rev else TEXT)
        self.lbl_right.configure(font=f(13, rev), text_color=TEXT if rev else MUTED)
        self.lbl_example.configure(text="๑๒๓  ➔  123" if rev else "123  ➔  ๑๒๓")

    def set_status(self, text: str, kind: str = "info"):
        color = {"ok": OK, "err": ERR}.get(kind, MUTED)
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def _save(self):
        self.config_data.update(hotkey=self.hotkey, reverse=self.reverse_mode)
        save_config(self.config_data)

    # ── events ──
    def on_toggle_mode(self):
        self.reverse_mode = bool(self.sw_mode.get())
        self._refresh_mode_ui()
        self._save()
        self.set_status("โหมด: ไทย ➔ อารบิก" if self.reverse_mode else "โหมด: อารบิก ➔ ไทย")

    def open_about(self):
        if self._about is not None and self._about.winfo_exists():
            self._about.focus()
            return
        self._about = AboutDialog(self)

    # ── เปลี่ยนคีย์ลัด ──
    def start_recording(self):
        self._recording = True
        self.btn_hotkey.configure(text="กดคีย์ลัดใหม่...  (Esc ยกเลิก)")
        self.bind("<KeyPress>", self._on_record_key)
        self.focus_force()

    def _stop_recording(self):
        self._recording = False
        self.unbind("<KeyPress>")
        self.btn_hotkey.configure(text=format_combo(self.hotkey))

    def _on_record_key(self, event):
        if event.keysym == "Escape":
            self._stop_recording()
            return "break"
        combo = combo_from_tk_event(event)
        if combo is None:  # ยังกดแค่ Ctrl/Shift/Alt
            return "break"
        parts = combo.split("+")
        if len(parts) < 2:
            self.set_status("ต้องกดร่วมกับ Ctrl, Shift หรือ Alt", "err")
            return "break"
        if "ctrl" in parts and "alt" in parts:
            self.set_status("ไม่แนะนำ Ctrl+Alt (ชนกับ AltGr ของแป้นพิมพ์ไทย)", "err")
            return "break"

        old = self.hotkey
        if self.hotkeys.register(combo):
            self.hotkey = combo
            self._save()
            self.set_status(f"ตั้งคีย์ลัดเป็น {format_combo(combo)} แล้ว", "ok")
        else:
            self.hotkeys.register(old)
            self.set_status(f"{format_combo(combo)} ถูกใช้โดยโปรแกรมอื่น ลองคีย์อื่น", "err")
        self._stop_recording()
        return "break"

    # ── ติดตามหน้าต่างล่าสุดที่ผู้ใช้ทำงานอยู่ (สำหรับปุ่ม "แปลงข้อความที่ไฮไลต์") ──
    def _track_foreground(self):
        if HAS_WIN32:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if (
                    hwnd
                    and win32process.GetWindowThreadProcessId(hwnd)[1] != os.getpid()
                    and win32gui.IsWindowVisible(hwnd)
                    and win32gui.GetClassName(hwnd) not in IGNORE_CLASSES
                ):
                    self._last_hwnd = hwnd
            except Exception:
                pass
        self.after(200, self._track_foreground)

    # ── DOCX ──
    def _setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_file_drop)

    def on_file_drop(self, event):
        # รองรับการลากหลายไฟล์ กรองเฉพาะนามสกุลที่รองรับ
        paths = [p for p in self.tk.splitlist(event.data) if Path(p).suffix.lower() in SUPPORTED]
        if paths:
            self.convert_files(paths)
        else:
            messagebox.showerror(
                APP_NAME, "โปรดวางเฉพาะไฟล์เอกสารที่รองรับ\n(Word · PowerPoint · Excel · ODF · RTF · TXT · HTML)",
                parent=self,
            )

    def on_select_file(self):
        paths = filedialog.askopenfilenames(parent=self, filetypes=FILETYPES)
        if paths:
            self.convert_files(list(paths))

    def convert_files(self, paths: list[str]):
        self.set_status("กำลังแปลงไฟล์...")
        reverse = self.reverse_mode

        def work():
            done, errors = [], []
            for p in paths:
                try:
                    done.append(process_file(p, reverse=reverse))
                except Exception as e:
                    errors.append(f"{Path(p).name}: {e}")
            self.after(0, lambda: self._files_done(done, errors))

        threading.Thread(target=work, daemon=True).start()

    def _files_done(self, done: list[str], errors: list[str]):
        if done:
            beep(1000, 150)
            self.set_status(f"แปลงสำเร็จ {len(done)} ไฟล์", "ok")
            messagebox.showinfo(APP_NAME, "แปลงไฟล์เรียบร้อยแล้ว\n\n" + "\n".join(done), parent=self)
        if errors:
            self.set_status("มีบางไฟล์แปลงไม่สำเร็จ", "err")
            messagebox.showerror(APP_NAME, "\n".join(errors), parent=self)

    # ── Clipboard ──
    def on_convert_clipboard(self):
        payload = get_clipboard_payload()
        if not payload.get("text"):
            self.set_status("ไม่พบข้อความในคลิปบอร์ด", "err")
            return
        set_clipboard_payload(convert_payload(payload, self.reverse_mode))
        beep(1000, 120)
        rich = "html" in payload or "rtf" in payload
        self.set_status(
            "แปลงแล้ว (คงฟอร์แมตเดิม) – กด Ctrl+V เพื่อวาง" if rich else "แปลงแล้ว – กด Ctrl+V เพื่อวาง", "ok"
        )

    # ── Selection ──
    def convert_selection(self, hwnd: int | None = None):
        """รันใน worker thread เสมอ  hwnd = หน้าต่างปลายทาง (None = ใช้หน้าต่างที่ active อยู่)"""
        if not self._busy.acquire(blocking=False):
            return
        try:
            self.set_status("กำลังแปลง...")
            if hwnd is not None and not focus_window(hwnd):
                self.set_status("สลับไปหน้าต่างปลายทางไม่ได้ ลองใช้คีย์ลัดแทน", "err")
                return
            wait_keys_released()

            if replace_in_word_selection(self.reverse_mode):
                beep(1200, 80)
                self.set_status("แปลงใน MS Word สำเร็จ (Keep Format)", "ok")
                return

            payload = copy_selection()
            if not payload.get("text"):
                self.set_status("ไม่พบข้อความที่เลือก (ไฮไลต์ข้อความก่อน)", "err")
                return
            set_clipboard_payload(convert_payload(payload, self.reverse_mode))
            time.sleep(0.08)
            send_ctrl(VK_V)  # วางทับข้อความที่เลือก ด้วยฟอร์แมตต้นฉบับ
            beep(1200, 80)
            self.set_status("แปลงข้อความสำเร็จ", "ok")
        except Exception as e:
            self.set_status(f"ผิดพลาด: {e}", "err")
        finally:
            self._busy.release()

    def on_convert_selection(self):
        if not self._last_hwnd:
            self.set_status("คลิกในโปรแกรมปลายทางก่อน แล้วค่อยกดปุ่มนี้", "err")
            return
        threading.Thread(target=self.convert_selection, args=(self._last_hwnd,), daemon=True).start()

    # ── อัปเดตเวอร์ชัน (GitHub Releases) ──
    def _check_update_bg(self):
        """ตรวจสอบอัปเดตอัตโนมัติตอนเปิดแอป (เงียบ ๆ ไม่บังคับ)"""
        def work():
            update = updater.check_for_update(APP_VERSION)
            self.after(0, lambda: self._render_update_state(update, silent=True))

        threading.Thread(target=work, daemon=True).start()

    def on_check_update(self):
        """ปุ่ม 'อัปเดต' — ตรวจสอบด้วยตนเอง"""
        if self._update_checking:
            return
        self._update_checking = True
        self.btn_update.configure(text="กำลังตรวจ...")
        self.set_status("กำลังตรวจสอบอัปเดต...")

        def work():
            update = updater.check_for_update(APP_VERSION)
            self.after(0, lambda: self._render_update_state(update, silent=False))

        threading.Thread(target=work, daemon=True).start()

    def _render_update_state(self, update, silent: bool):
        """แสดงผลการตรวจสอบอัปเดต update=None = ใช้เวอร์ชันล่าสุดแล้ว"""
        self._update_checking = False
        self.btn_update.configure(text="อัปเดต")
        if update:
            self._prompt_update(update)
        elif not silent:
            self.set_status(f"คุณใช้เวอร์ชันล่าสุดแล้ว ({APP_VERSION})", "ok")
            self.btn_update.configure(text_color=OK)

    def _prompt_update(self, update: dict):
        """ถามผู้ใช้ว่าจะอัปเดตหรือไม่ ถ้าตกลงให้ดาวน์โหลด + แทนที่เมื่อปิดแอป"""
        notes = (update.get("notes") or "").strip()
        msg = f"มีเวอร์ชันใหม่ {update['version']} พร้อมใช้งาน\n(คุณใช้เวอร์ชัน {APP_VERSION})"
        if notes:
            msg += f"\n\nบันทึกการเปลี่ยนแปลง:\n{notes[:800]}"
        ans = messagebox.askyesno(
            f"อัปเดต {APP_NAME}",
            msg + "\n\nต้องการดาวน์โหลดและอัปเดตตอนนี้หรือไม่?",
            parent=self,
        )
        if not ans:
            self.set_status(f"มีเวอร์ชันใหม่ {update['version']} — ยังไม่อัปเดต", "info")
            return
        self.set_status("กำลังดาวน์โหลดอัปเดต...")
        self.btn_update.configure(text="ดาวน์โหลด...")

        def work():
            ok = updater.download_and_apply(update)
            self.after(0, lambda: self._apply_result(ok, update))

        threading.Thread(target=work, daemon=True).start()

    def _apply_result(self, ok: bool, update: dict):
        self.btn_update.configure(text="อัปเดต")
        if ok:
            self.set_status(f"ดาวน์โหลดเวอร์ชัน {update['version']} แล้ว — ปิดแอปเพื่ออัปเดต", "ok")
            messagebox.showinfo(
                APP_NAME,
                f"ดาวน์โหลดเวอร์ชัน {update['version']} เรียบร้อย\n\n"
                "กรุณาปิดโปรแกรมเพื่อให้อัปเดตเสร็จสมบูรณ์ แล้วโปรแกรมจะเปิดใหม่อัตโนมัติ",
                parent=self,
            )
        else:
            self.set_status("ดาวน์โหลดอัปเดตไม่สำเร็จ", "err")
            messagebox.showerror(APP_NAME, "ดาวน์โหลดอัปเดตไม่สำเร็จ กรุณาลองใหม่อีกครั้ง", parent=self)

    def _on_close(self):
        self.hotkeys.unregister()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    register_fonts()
    EasySarabunApp().mainloop()
