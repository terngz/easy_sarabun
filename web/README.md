# Easy Sarabun Web

เวอร์ชันเว็บของ Easy Sarabun — แปลงตัวเลขไทย/อารบิกในไฟล์เอกสารโดยคงรูปแบบเดิม
**ประมวลผลในเบราว์เซอร์ของผู้ใช้ 100% (client-side)** ไม่มีการอัปโหลดไฟล์ ไม่ต้องมี
server / database / R2 สำหรับจัดเก็บไฟล์ (footprint ≈ 0)

## ลักษณะสำคัญ

- **ไม่ต้องติดตั้ง** — ผู้ใช้แค่เปิด URL ในเบราว์เซอร์เท่านั้น
- **เต็มที่ client-side** — ไฟล์ไม่เคยออกจากเครื่องผู้ใช้
- **reuse โค้ด/design เดิม** — port ตรรกะจาก `engine.py` / `file_handler.py` /
  `clip_format.py` มาเป็น JS และ reuse design token จาก `theme.py` + `DESIGN.md`

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | หน้าที่ |
|---|---|
| [`engine.js`](engine.js) | แปลงตัวเลข (`to_thai`/`to_arabic`) — port จาก `engine.py` |
| [`web.js`](web.js) | แปลงไฟล์ (`EasyWeb`) — port จาก `file_handler.py` + `clip_format.py` |
| [`app.js`](app.js) | UI logic (drag & drop, mode, status, download, FAQ) |
| [`index.html`](index.html) | หน้าเว็บ (รวม SEO/structured data + FAQ + download CTA) |
| [`styles.css`](styles.css) | สไตล์ (token จาก `theme.py`, ธีม dark ตาม `DESIGN.md`) |
| [`test.js`](test.js) | Node sanity tests (13 ข้อ) |

## ชนิดไฟล์ที่รองรับ

`.docx .docm .pptx .pptm .xlsx .xlsm .odt .ods .odp .rtf .txt .md .csv .html .htm`

> **ไม่รองรับ** `.doc .ppt .xls` (legacy) — เดิมต้องใช้ MS Office/LibreOffice ผ่าน
> `subprocess` ([`file_handler.py`](../file_handler.py)) ซึ่งเบราว์เซอร์ทำไม่ได้

## วิธีทดสอบบนเครื่อง

ต้องรันผ่าน server อยู่แล้ว ไม่งั้น `module`/`fetch`/CDN ไม่โหลด (เปิด `file://` ตรง ๆ ไม่ได้):

```bash
cd web
python -m http.server 8000
# เปิด http://localhost:8000
```
หรือใช้ `npx serve .` ก็ได้

## Deploy ขึ้น Cloudflare Pages

โฟลเดอร์ `web/` นี้เป็น **static site เต็มตัว** — แค่ชี้ Pages ไปที่มันก็ได้ทั้งเว็บ

### วิธี A — Dashborad (เร็วสุด)
1. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Pages** → **Upload assets**
2. เลือกอัปโหลด **เนื้อหาภายใน `web/`** (engine.js, web.js, app.js, index.html, styles.css)
3. ตั้งชื่อโปรเจกต์ → Deploy → ได้ URL ฟรี เช่น `easy-sarabun-web.pages.dev`

### วิธี B — Connected Git repo (แนะนำสำหรับอัปเดตอัตโนมัติ)
1. push repo ขึ้น GitHub
2. Cloudflare Pages → **Create project** → connect กับ repo
3. ตั้งค่า **Build configuration**:
   - **Build command**: `(ว่าง / ไม่มี build step)`
   - **Build output directory**: `web`
4. Deploy — ทุกครั้งที่ push ไปยัง branch default จะ build อัตโนมัติ

> หมายเหตุ: ถ้าต้องการให้ logo (`assets/icon.png`) แสดงในเว็บ ต้อง copy `assets/icon.png`
> ไปไว้ที่โปรเจกต์ Pages (เช่น วาง `assets/` ไว้ข้าง `index.html` ใน output) หรือใช้
> ภาพ hosting อื่น — ตอนนี้หน้าเว็บจะซ่อน logo ถ้าโหลดไม่เจอ (ไม่ทำให้ app พัง)

## ฟีเจอร์ที่เพิ่มในหน้าเว็บ

- **FAQ / วิธีใช้** — section คำถามที่พบบ่อยแบบ accordion (เปิด/ปิดได้, ตัวแรกเปิดไว้)
- **ปุ่มดาวน์โหลด desktop** — CTA ที่ footer ลิงก์ไปยัง
  https://github.com/terngz/easy_sarabun/releases สำหรับผู้ที่ต้องการฟีเจอร์
  desktop (แปลงข้อความที่ไฮไลต์ใน Word / จากคลิปบอร์ด / hotkey)
- **SEO & structured data** — meta description/keywords, Open Graph, Twitter Card,
  JSON-LD `WebApplication`, `BreadcrumbList`, และ `FAQPage` (ช่วยเรื่องผลค้นหา
  และ AI crawler)

## ข้อจำกัดเมื่อเทียบกับเวอร์ชัน desktop

- ไม่มี global hotkey / การดัก clipboard ระบบ (เบราว์เซอร์ทำไม่ได้)
- Legacy `.doc/.ppt/.xls` ไม่รองรับ
- ขึ้นอยู่กับไลบรารีภายนอก (JSZip จาก CDN) — ควร vendor ไว้ในเครื่องหากต้องการ offline

## แนวคิดการออกแบบ (อ้างอิง DESIGN.md)

- ธีม **dark ล็อก** ตาม [`DESIGN.md`](../DESIGN.md)
- พาเลตต์/สไตล์มาจาก [`theme.py`](../theme.py) token เดียวกัน เปลี่ยนสไตล์ที่
  [`styles.css`](styles.css) เป็นจุดเดียว
