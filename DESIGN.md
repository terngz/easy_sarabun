# Easy Sarabun — Design System

แก้ค่าทั้งหมดที่ `theme.py` ที่เดียว

## Tokens
| หมวด | ค่า |
|---|---|
| สีหลัก | `ACCENT` เขียวลึก `#1F6B57` (dark สว่างสด `#34D399`) · hover `#1A5A49` (dark `#2BB584`) — โทน mix: ลึกใน light / สว่างใน dark |
| พื้น/เส้น | `SURFACE` `#F4F5F2` (dark `#171A18`) · `BORDER` `#D9DDD5` (dark `#2D3330`) |
| ข้อความ | `TEXT` `#18211C` · `MUTED` `#5F6B63` สำหรับข้อความรอง |
| สถานะ | `SUCCESS` เขียว `#2F7D4F` · `DANGER` แดง `#C0392B` |
| Ko-fi | `#78756c` (ใช้เฉพาะปุ่ม "เลี้ยงกาแฟ") |
| ฟอนต์ | Kanit (Regular / Medium) · fallback Tahoma (สำรอง Mitr) |
| ขนาดตัวอักษร | caption 11 · small 12 · body 13 · button 14 · title 24 · display 26 |
| ระยะห่าง | xs 4 · sm 8 · md 14 · lg 20 · xl 28 |
| มุมโค้ง | button 10 · card 14 · pill 14 |

> ทุกค่า (สี/ฟอนต์) นิยามที่ `theme.py` เพียงที่เดียว — `main.py` นำเข้า (`import theme`) ไม่นิยามซ้ำ ถ้าจะปรับสี ไปแก้ที่ `theme.py`

## Components
| ชื่อ | variants / sizes | ใช้เมื่อ |
|---|---|---|
| `button` | primary · outline · ghost · chip · kofi  /  lg 44 · md 38 · sm 28 | primary = การกระทำหลัก 1 ปุ่มต่อหน้า, outline = การกระทำรอง |
| `card` | — | จัดกลุ่มตัวเลือก (โหมดการแปลง) |
| `dropzone` | — | พื้นที่ลาก/คลิกเลือกไฟล์ |
| Mode switch | สวิตช์กลาง + ป้ายซ้าย/ขวา | ฝั่งที่ใช้งานอยู่ตัวหนา อีกฝั่งสี MUTED |
| Settings (⚙) | ปุ่มเฟือง ขวาสุด header → `SettingsDialog` | เวอร์ชัน + ปุ่มตรวจสอบอัปเดต, สลับ ธีมสว่าง/มืด + คืนค่า ตาม Windows, กาแฟ, ลิขสิทธิ์ |
| Update banner | แถบแจ้งเตือน ACCENT ด้านล่าง (ตรงตำแหน่งสถานะ) | โผล่เมื่อพบเวอร์ชันใหม่ (ไม่ต้องกด modal) · ปุ่มขาว "อัปเดต ↓" เริ่มดาวน์โหลด |

## States
- ปุ่ม: default / hover (สีเข้มขึ้นหรือพื้น SURFACE) — ยังไม่มี disabled/loading (สถานะแจ้งที่แถบล่างแทน)
- สถานะ (แถบล่าง): info = MUTED · ok = SUCCESS · err = DANGER

## ธีม (Dark แบบตายตัว)
- ธีมถูก **ล็อกเป็นโหมดมืด (Dark)** ตลอดเวลา — ปิดฟีเจอร์เปลี่ยนธีมออก (เดิมมี bug แอปค้างเมื่อสลับ Light/Dark ในหน้าต่างตั้งค่า)
- เรียกผ่าน `ctk.set_appearance_mode("Dark")` ครั้งเดียวตอนสตาร์ท · ไม่มีสวิตช์/ปุ่มเปลี่ยนธีมในหน้าต่างตั้งค่าอีก
- ลบโค้ดที่ตายแล้วออก: `set_appearance()`, `_sync_theme()`, `_on_toggle_dark()`, `_on_auto()`, `_sync_status_labels()` และคีย์ `appearance` ใน `_save()`

## Audit (สรุป)
- ไม่มีสี hex ฝังใน `main.py` แล้ว — `main.py` นำเข้าค่าจาก `theme.py` (ยกเว้น `white` บนปุ่ม primary/kofi และ knob ของสวิตช์)
- ปุ่มทุกตัวสร้างผ่าน `button()`/`card()`/`dropzone()` ชื่อ/ขนาด/มุมโค้งจึงสม่ำเสมอ
- ควรเพิ่มภายหลัง: สถานะ disabled ระหว่างแปลงไฟล์, focus ring สำหรับคีย์บอร์ด
- Accessibility: `MUTED` (light) `#5F6B63` คอนทราสต์บน `SURFACE` ผ่าน AA · ปุ่ม primary ตัวหนังสือขาวบน ACCENT ผ่าน AA ในทั้งสองธีม

## อัปเดต (Update flow)
- Build เป็น **onefile portable** (EXE เดียว ไม่มี installer) — อัปเดต = ดาวน์โหลด zip จาก GitHub Releases, แตกใน temp, `.bat` รอให้ process ตาย (tasklist) แล้ว `copy /y` ทับ `sys.executable` แล้ว `start` เปิดใหม่
- UX: พบเวอร์ชันใหม่ → **แถบแจ้งเตือน** ด้านล่าง (ตำแหน่งเดียวกับสถานะ) ไม่ขึ้น modal รบกวน · กด "อัปเดต ↓" → ดาวน์โหลด แล้วบอกให้ปิดแอปเพื่อจบการอัปเดต

## ไอคอน
วาง `assets/icon.jpg` (จัตุรัสจะดีที่สุด) แล้วรัน `python make_icon.py` จะได้ `icon.ico` + `icon.png`
