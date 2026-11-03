"""Easy Sarabun - global hotkey ผ่าน Win32 RegisterHotKey

ข้อดีกว่า pynput: ไม่ขึ้นกับ layout แป้นพิมพ์ (ใช้ virtual-key), คีย์ลัดถูกดักไว้
(ไม่ทะลุไปให้แอปอื่น เช่น Ctrl+Shift+T ของเบราว์เซอร์) และรู้ทันทีถ้าคีย์ซ้ำกับโปรแกรมอื่น
"""
from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

MOD = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4}
MOD_NOREPEAT = 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012


def parse_combo(combo: str) -> tuple[int, int]:
    """'ctrl+shift+t' -> (modifiers, virtual-key)"""
    mods, vk = 0, 0
    for part in combo.lower().split("+"):
        part = part.strip()
        if part in MOD:
            mods |= MOD[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part.startswith("f") and part[1:].isdigit() and 1 <= int(part[1:]) <= 12:
            vk = 0x70 + int(part[1:]) - 1
        else:
            raise ValueError(f"คีย์ไม่รองรับ: {part}")
    if not mods or not vk:
        raise ValueError("ต้องมีปุ่ม Ctrl/Shift/Alt อย่างน้อย 1 ปุ่ม และปุ่มหลัก 1 ปุ่ม")
    return mods, vk


def format_combo(combo: str) -> str:
    return " + ".join(p.capitalize() if len(p) > 1 else p.upper() for p in combo.split("+"))


def combo_from_tk_event(event) -> str | None:
    """สร้าง combo จาก tkinter KeyPress (Windows: event.keycode = virtual-key)
    คืน None ถ้ายังกดแค่ปุ่มโมดิฟายเออร์"""
    vk = event.keycode
    if 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
        key = chr(vk).lower()
    elif 0x70 <= vk <= 0x7B:
        key = f"f{vk - 0x70 + 1}"
    else:
        return None
    parts = []
    if event.state & 0x4:
        parts.append("ctrl")
    if event.state & 0x20000:
        parts.append("alt")
    if event.state & 0x1:
        parts.append("shift")
    return "+".join(parts + [key])


class HotkeyManager:
    def __init__(self, callback):
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._tid: int | None = None

    def register(self, combo: str) -> bool:
        """ลงทะเบียนคีย์ลัด (แทนอันเดิม) คืน False ถ้าถูกโปรแกรมอื่นใช้อยู่"""
        if os.name != "nt":
            return False
        self.unregister()
        mods, vk = parse_combo(combo)
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        ready, state = threading.Event(), {}

        def run():
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # สร้าง message queue
            state["tid"] = kernel32.GetCurrentThreadId()
            state["ok"] = bool(user32.RegisterHotKey(None, 1, mods | MOD_NOREPEAT, vk))
            ready.set()
            if not state["ok"]:
                return
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    threading.Thread(target=self._callback, daemon=True).start()
            user32.UnregisterHotKey(None, 1)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        ready.wait(2)
        if state.get("ok"):
            self._thread, self._tid = thread, state["tid"]
            return True
        return False

    def unregister(self):
        if self._thread and self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            self._thread.join(1)
        self._thread = self._tid = None
