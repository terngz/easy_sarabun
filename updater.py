from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

OWNER = "terngz"
REPO = "easy_sarabun"
API_URL = f"https://api.github.com/repos/terngz/easy_sarabun/releases/latest"
REQUEST_TIMEOUT = 20
UA = "easy_sarabun-updater"


# ───────────────────────── Semver ─────────────────────────
def _parse_version(s: str) -> tuple[int, ...]:
    """'v1.2.3' / '1.2' -> (1, 2, 3)"""
    numbers = re.findall(r"\d+", s or "")
    return tuple(map(int, numbers)) if numbers else (0, 0, 0)


def is_newer(remote_version: str, current_version: str) -> bool:
    return _parse_version(remote_version) > _parse_version(current_version)


# ───────────────────────── Check ─────────────────────────
def check_for_update(current_version: str) -> dict | None:
    """เช็คว่ามีเวอร์ชันใหม่กว่าปัจจุบันหรือไม่
    คืน None ถ้าไม่มีเวอร์ชันใหม่ / เกิดข้อผิดพลาด"""
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    version = str(data.get("tag_name", "")).strip()
    if not version or not is_newer(version, current_version):
        return None

    url = None
    assets = data.get("assets", []) or []
    
    # 1. ค้นหาไฟล์ .zip หรือ .exe อัตโนมัติ (ไม่ต้องเช็กชื่อเต็ม)
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".zip") or name.endswith(".exe"):
            url = asset.get("browser_download_url")
            break

    # 2. ถ้าไม่เจอไฟล์นามสกุลข้างต้น ให้ดึงไฟล์แรกใน assets
    if not url and assets:
        url = assets[0].get("browser_download_url")

    if not url:
        return None

    return {
        "version": version,
        "notes": (data.get("body") or "").strip(),
        "url": url,
        "html_url": data.get("html_url") or "",
    }


# ───────────────────────── Download + apply ─────────────────────────
def download_and_apply(update: dict) -> bool:
    """ดาวน์โหลดและแตกไฟล์ .zip (หรือ .exe) แล้ววางสคริปต์ .bat เพื่อคัดลอกทับเมื่อปิดแอป"""
    try:
        req = urllib.request.Request(update["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()

        temp_dir = Path(tempfile.gettempdir())
        downloaded_url = update["url"].lower()
        new_exe_path = None

        # กรณีไฟล์ที่โหลดมาเป็น .zip ให้จัดการแตกไฟล์ออกมาก่อน
        if downloaded_url.endswith(".zip"):
            zip_tmp = temp_dir / f"easy_sarabun_update_{os.getpid()}.zip"
            zip_tmp.write_bytes(data)
            
            extract_folder = temp_dir / f"easy_sarabun_extracted_{os.getpid()}"
            with zipfile.ZipFile(zip_tmp, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            
            # ค้นหาไฟล์ .exe ภายในโฟลเดอร์ที่แตกออกมา
            exe_files = list(extract_folder.rglob("*.exe"))
            if exe_files:
                new_exe_path = exe_files[0]
            
            # ลบไฟล์ zip ชั่วคราว
            try:
                zip_tmp.unlink()
            except Exception:
                pass
        else:
            # กรณีอัปโหลดเป็นไฟล์ .exe ตรงๆ
            new_exe_path = temp_dir / f"easy_sarabun_update_{os.getpid()}.exe"
            new_exe_path.write_bytes(data)

        if not new_exe_path or not new_exe_path.exists():
            return False

        current_exe = Path(sys.executable or sys.argv[0]).resolve()
        bat = temp_dir / f"easy_sarabun_apply_{os.getpid()}.bat"

        # เขียน Batch script: รอให้แอปปิด (จำกัดรอบ ไม่วนไม่รู้จบ) แล้วคัดลอกใหม่ทับพร้อมตรวจผล
        # ใช้ self-restart flag เพื่อกันแอปใหม่เปิดขึ้นมาแล้วทำ update ซ้ำ
        marker = bat.with_suffix(".flag")
        bat.write_text(
            "@echo off\r\n"
            "setlocal\r\n"
            "set /a tries=0\r\n"
            ":wait\r\n"
            f'tasklist /FI "IMAGENAME eq {current_exe.name}" 2>nul | find /I "{current_exe.name}" >nul\r\n'
            "if not %errorlevel%==0 goto replace\r\n"
            "set /a tries+=1\r\n"
            "if %tries% geq 60 goto replace\r\n"   # ~60 วินาทีสูงสุด กรณี process ยังไม่ยอมตาย
            "timeout /t 1 /nobreak >nul\r\n"
            "goto wait\r\n"
            ":replace\r\n"
            f'copy /y "{new_exe_path}" "{current_exe}" >nul\r\n'
            "if %errorlevel%==0 (\r\n"
            f'  echo done > "{marker}"\r\n'
            f'  start "" /d "{current_exe.parent}" "{current_exe.name}"\r\n'
            f'  del "{new_exe_path}" >nul 2>&1\r\n'
            ")\r\n"
            f'del "{bat}" >nul 2>&1\r\n'
            "exit /b 0\r\n",
            encoding="utf-8",
        )

        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0),
            close_fds=True,
        )
        return True
    except Exception as e:
        print(f"Update failed: {e}")
        return False