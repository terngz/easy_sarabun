# Easy Sarabun Web — Deploy ผ่าน Cloudflare Worker + R2

วิธีแยกหน้าเว็บ Easy Sarabun ออกจากเว็บหลัก (Astro) โดยใช้ **Cloudflare Worker + R2**
เพื่อให้แก้ไขหน้าเว็บนี้ deploy เฉพาะ Worker นี้ได้เอง ไม่ต้องไป deploy กับเว็บหลัก

URL เป้าหมาย: `https://www.konnextgroup.com/apps/easysarabun/`

---

## โครงสร้าง

```
worker/
  index.js      # Cloudflare Worker — serve static files จาก R2
  upload.ps1    # สคริปต์อัปโหลด web/ ขึ้น R2
  README.md     # เอกสารนี้
web/            # ตัวแอป (index.html, styles.css, engine.js, web.js, app.js)
```

---

## R2 bucket

- bucket: **`konnext-web`** (สร้างไว้แล้ว)
- key prefix: **`apps/easysarabun/`**
  - เช่น `apps/easysarabun/index.html`, `apps/easysarabun/styles.css`

Worker ตัด prefix `apps/easysarabun/` ออกจาก URL path แล้ว fetch จาก bucket
(URL `/apps/easysarabun/styles.css` → key `apps/easysarabun/styles.css`)

---

## ขั้นตอน deploy

### 1) อัปโหลดไฟล์เว็บขึ้น R2

```powershell
npm i -g wrangler
wrangler login

powershell -ExecutionPolicy Bypass -File upload.ps1
```

ตรวจผล:

```bash
wrangler r2 object list konnext-web --prefix apps/easysarabun/
```

### 2) สร้าง/อัปเดต Worker

1. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Worker**
   (หรือใช้โปรเจกต์ Worker ที่มีอยู่)
2. แก้ `index.js` ให้เป็นเนื้อหาของ `worker/index.js`
3. **Settings → Bindings → Add → R2 bucket binding**:
   - Variable name: `EASY_SARABUN_BUCKET`
   - Bucket: `konnext-web`
4. **Settings → Triggers → Routes** — mount ลงโดเมน:
   - Route: `www.konnextgroup.com/apps/easysarabun/*`
   - Zone: `konnextgroup.com`
5. Save & Deploy

> ถ้า Worker เดิม (เว็บหลัก) รองรับ route อยู่แล้ว ให้เพิ่ม route `apps/easysarabun/*`
> ใน Worker เดิม และย้ายโค้ด serve-FROM-R2 เข้าไปด้วย (แล้วไม่ต้องสร้าง Worker ใหม่)

### 3) เปิดใช้งาน

```
https://www.konnextgroup.com/apps/easysarabun/
```

---

## สิ่งที่ Worker ทำ

- เสิร์ฟ static files (`index.html`, `styles.css`, `engine.js`, `web.js`, `app.js`) จาก R2
- ตั้ง `Content-Type` ตามนามสกุล + `Cache-Control` (index = สั้น, asset = immutable)
- root `/apps/easysarabun/` → `index.html`
- deep link / path ที่ไม่มีนามสกุล → fallback ไป `index.html` (SPA)

> หมายเหตุ: `web/` ใช้ relative URLs อยู่แล้ว (`styles.css`, `engine.js`, ...)
> ดังนั้น mount ใน subpath `/apps/easysarabun/` ได้เลย ไม่ต้องแก้โค้ดเว็บ

---

## แก้ไขหน้าคราวหน้า

```powershell
# แก้ไฟล์ใน web/ เสร็จแล้ว ก็แค่อัปโหลดใหม่ แล้ว Worker เสิร์ฟให้ทันที
powershell -ExecutionPolicy Bypass -File upload.ps1
```

ไม่ต้อง deploy เว็บหลัก (Astro) เลย
