# Easy Sarabun — Design System

แก้ค่าทั้งหมดที่ `theme.py` ที่เดียว

## Tokens
| หมวด | ค่า |
|---|---|
| สีหลัก | `ACCENT` เขียวหม่น `#2f6f62` (dark `#4a9a8a`) · hover `#265a50` |
| พื้น/เส้น | `SURFACE` `#f5f5f3` · `BORDER` `#dcdcd8` (มี dark คู่กันทุกค่า) |
| ข้อความ | `TEXT` · `MUTED` สำหรับข้อความรอง |
| สถานะ | `SUCCESS` เขียว · `DANGER` แดง |
| Ko-fi | `#78756c` (ใช้เฉพาะปุ่ม "เลี้ยงกาแฟ") |
| ฟอนต์ | Mitr (Regular / Medium) · fallback Tahoma |
| ขนาดตัวอักษร | caption 11 · small 12 · body 13 · button 14 · title 24 · display 26 |
| ระยะห่าง | xs 4 · sm 8 · md 14 · lg 20 · xl 28 |
| มุมโค้ง | button 10 · card 14 · pill 14 |

## Components
| ชื่อ | variants / sizes | ใช้เมื่อ |
|---|---|---|
| `button` | primary · outline · ghost · chip · kofi  /  lg 44 · md 38 · sm 28 | primary = การกระทำหลัก 1 ปุ่มต่อหน้า, outline = การกระทำรอง |
| `card` | — | จัดกลุ่มตัวเลือก (โหมดการแปลง) |
| `dropzone` | — | พื้นที่ลาก/คลิกเลือกไฟล์ |
| Mode switch | สวิตช์กลาง + ป้ายซ้าย/ขวา | ฝั่งที่ใช้งานอยู่ตัวหนา อีกฝั่งสี MUTED |

## States
- ปุ่ม: default / hover (สีเข้มขึ้นหรือพื้น SURFACE) — ยังไม่มี disabled/loading (สถานะแจ้งที่แถบล่างแทน)
- สถานะ (แถบล่าง): info = MUTED · ok = SUCCESS · err = DANGER

## Audit (สรุป)
- ไม่มีสี hex ฝังใน `main.py` แล้ว (ยกเว้น `white` บนปุ่ม primary/kofi และ knob ของสวิตช์)
- ปุ่มทุกตัวสร้างผ่าน `button()` ชื่อ/ขนาด/มุมโค้งจึงสม่ำเสมอ
- ควรเพิ่มภายหลัง: สถานะ disabled ระหว่างแปลงไฟล์, focus ring สำหรับคีย์บอร์ด
- Accessibility: ปรับ `MUTED` (light) เป็น `#6a6862` แล้ว คอนทราสต์บน SURFACE ได้ 5.1:1 (ผ่าน AA) · ปุ่ม primary ตัวหนังสือขาวบน ACCENT 5.9:1 · ปุ่ม Ko-fi 4.6:1

## ไอคอน
วาง `assets/icon.jpg` (จัตุรัสจะดีที่สุด) แล้วรัน `python make_icon.py` จะได้ `icon.ico` + `icon.png`
