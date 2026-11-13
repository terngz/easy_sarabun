/**
 * Easy Sarabun Web — Cloudflare Worker serving static files from R2.
 *
 * ใช้ mount ที่ path `/apps/easysarabun/*` บนโดเมน konnextgroup.com
 * โดยไม่ยุ่งกับเว็บหลัก (Astro) — แก้ไขหน้าเว็บนี้ deploy เฉพาะ Worker นี้ได้เอง
 *
 * การทำงาน:
 *   - Request ที่เข้า `https://www.konnextgroup.com/apps/easysarabun/<file>`
 *     จะถูกตัด prefix `apps/easysarabun/` แล้ว fetch จาก R2 bucket
 *     (key ใน bucket = `apps/easysarabun/<file>`)
 *   - ตั้ง Content-Type ตามนามสกุล และตั้ง Cache-Control สำเร็จรูป
 *   - root / ไม่มีชื่อไฟล์ -> เสิร์ฟ index.html
 *   - path ที่ไม่มีนามสกุล (เช่น deep link /faq) -> เสิร์ฟ index.html
 */

// prefix ใน bucket ที่ไฟล์ถูกอัปโหลดไว้ (ต้องตรงกับ upload.ps1)
const KEY_PREFIX = "apps/easysarabun/";

// หน้าที่จะถูกเสิร์ฟเมื่อเข้า root หรือเจอ path ที่ไม่มีนามสกุล (SPA fallback)
const INDEX_FILE = "index.html";

// อนุญาต cache ในเบราว์เซอร์ที่เนื้อหาไม่เปลี่ยน
const INDEX_CACHE = "public, max-age=60, stale-while-revalidate=86400";
const ASSET_CACHE = "public, max-age=86400, immutable";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
  ".pdf": "application/pdf",
  ".xml": "application/xml; charset=utf-8",
  ".map": "application/json; charset=utf-8",
};

function extOf(pathname) {
  const m = /(\.[a-zA-Z0-9]+)$/.exec(pathname);
  return m ? m[1].toLowerCase() : "";
}

function contentTypeFor(pathname) {
  return MIME[extOf(pathname)] || "application/octet-stream";
}

// ตัด query string, normalize path โดยไม่ให้ escape ออกจาก prefix
function normalizePath(pathname) {
  // ลบ leading slash
  let p = pathname.replace(/^\/+/, "");
  // กัน path traversal (../) ขึ้นไปนอก prefix
  const parts = [];
  for (const seg of p.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      if (parts.length) parts.pop();
      continue;
    }
    parts.push(seg);
  }
  p = parts.join("/");
  return p;
}

async function serveFile(env, key) {
  const obj = await env.EASY_SARABUN_BUCKET.get(key);
  if (!obj) return null;
  const headers = new Headers(obj.httpMetadata?.customMetadata || {});
  headers.set("Content-Type", contentTypeFor(key));
  return new Response(obj.body, { status: 200, headers });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    void ctx;

    // เฉพาะ GET/HEAD เท่านั้น
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // normalize path (ตัด prefix apps/easysarabun ออกให้เหลือ key ใน bucket)
    const normalized = normalizePath(url.pathname);

    // ถ้า path ขึ้นต้นด้วย prefix ให้ตัดออก ไม่งั้น key จะซ้ำ
    let rel = normalized;
    if (rel.startsWith(KEY_PREFIX)) {
      rel = rel.slice(KEY_PREFIX.length);
    }

    // root -> index
    let key;
    if (rel === "" || rel.endsWith("/")) {
      key = KEY_PREFIX + INDEX_FILE;
    } else {
      key = KEY_PREFIX + rel;
    }

    let obj = await serveFile(env, key);

    // ถ้าไฟล์ไม่มีนามสกุล (deep link / SPA route) -> fallback ไป index.html
    if (!obj && extOf(rel) === "") {
      obj = await serveFile(env, KEY_PREFIX + INDEX_FILE);
    }

    if (!obj) {
      return new Response("Not Found", { status: 404 });
    }

    // ตั้ง cache ตามชนิดไฟล์
    const isIndex = key.endsWith("/" + INDEX_FILE) || key === KEY_PREFIX + INDEX_FILE;
    obj.headers.set(
      "Cache-Control",
      isIndex ? INDEX_CACHE : ASSET_CACHE
    );

    return obj;
  },
};
