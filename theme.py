"""Easy Sarabun - design tokens + component factories

แก้สี/ขนาด/มุมโค้งที่ไฟล์นี้ที่เดียว ทุกหน้าจอจะเปลี่ยนตาม (ดู DESIGN.md)
ค่าสีเป็น (light, dark) ตามรูปแบบของ customtkinter
"""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

# ───────────── Color tokens ─────────────
ACCENT = ("#2f6f62", "#4a9a8a")
ACCENT_HOVER = ("#265a50", "#3d8374")
SURFACE = ("#f5f5f3", "#262626")      # พื้นการ์ด / ปุ่มรอง
BORDER = ("#dcdcd8", "#3b3b3b")
TEXT = ("#1f1f1f", "#ececec")
MUTED = ("#6a6862", "#9b9993")
SUCCESS = ("#2f7d4f", "#5fbf86")
DANGER = ("#c0392b", "#e67e73")
KOFI = "#78756c"
KOFI_HOVER = "#66635b"

# ───────────── Spacing / radius / type tokens ─────────────
SPACE = {"xs": 4, "sm": 8, "md": 14, "lg": 20, "xl": 28}
RADIUS = {"button": 10, "card": 14, "pill": 14}
TYPE = {"caption": 11, "small": 12, "body": 13, "button": 14, "title": 24, "display": 26}


# ───────────── Typography ─────────────
class Fonts:
    regular = "Tahoma"   # fallback
    medium = "Tahoma"

    @classmethod
    def detect(cls, root) -> None:
        families = set(tkfont.families(root))
        if "Mitr" in families:
            cls.regular = "Mitr"
            cls.medium = "Mitr Medium" if "Mitr Medium" in families else "Mitr"


def font(size: int | str, bold: bool = False) -> ctk.CTkFont:
    """font('body') หรือ font(14, True)"""
    size = TYPE.get(size, size) if isinstance(size, str) else size
    if bold and Fonts.medium != Fonts.regular:
        return ctk.CTkFont(family=Fonts.medium, size=size)
    return ctk.CTkFont(family=Fonts.regular, size=size, weight="bold" if bold else "normal")


# ───────────── Components ─────────────
_VARIANTS = {
    "primary": dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white", border_width=0),
    "outline": dict(fg_color="transparent", hover_color=SURFACE, text_color=ACCENT,
                    border_width=1, border_color=ACCENT),
    "ghost": dict(fg_color="transparent", hover_color=SURFACE, text_color=TEXT,
                  border_width=1, border_color=BORDER),
    "chip": dict(fg_color=SURFACE, hover_color=BORDER, text_color=TEXT, border_width=0),
    "kofi": dict(fg_color=KOFI, hover_color=KOFI_HOVER, text_color="white", border_width=0),
}
_SIZES = {
    "lg": dict(height=44, corner_radius=RADIUS["button"], font=(TYPE["button"], True)),
    "md": dict(height=38, corner_radius=RADIUS["button"], font=(TYPE["body"], False)),
    "sm": dict(height=28, corner_radius=RADIUS["pill"], font=(TYPE["small"], False)),
}


def button(master, text: str, variant: str = "primary", size: str = "lg", **kw) -> ctk.CTkButton:
    """variant: primary | outline | ghost | chip | kofi     size: lg | md | sm"""
    spec = dict(_SIZES[size])
    size_px, bold = spec.pop("font")
    return ctk.CTkButton(master, text=text, font=font(size_px, bold), **spec, **_VARIANTS[variant], **kw)


def card(master, **kw) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color=SURFACE, corner_radius=RADIUS["card"], **kw)


def dropzone(master) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color="transparent", border_width=1,
                        border_color=BORDER, corner_radius=RADIUS["card"])
