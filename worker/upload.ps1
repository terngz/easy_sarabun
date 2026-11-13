# ---------------------------------------------------------------------------
# อัปโหลดไฟล์เว็บ (web/) ขึ้น R2 bucket "konnext-web" ที่ key apps/easysarabun/
# ใช้ร่วมกับ Cloudflare Worker (worker/index.js) ที่ serve static files จาก R2
#
# ข้อกำหนด: ติดตั้ง wrangler แล้ว และ login เรียบร้อย
#   npm i -g wrangler
#   wrangler login
#
# การใช้งาน:
#   powershell -ExecutionPolicy Bypass -File upload.ps1
#
# ตัวเลือก:
#   -KeyPrefix "อื่นๆ/"   เพื่อเปลี่ยน prefix (default apps/easysarabun/)
# ---------------------------------------------------------------------------

param(
  [string]$Bucket = "konnext-web",
  [string]$KeyPrefix = "apps/easysarabun/",
  [string]$Source = "$PSScriptRoot\..\web"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command wrangler -ErrorAction SilentlyContinue)) {
    Write-Error "ไม่พบ wrangler กรุณา: npm i -g wrangler ก่อน"
}

$files = Get-ChildItem -Path $Source -Recurse -File

if ($files.Count -eq 0) {
    Write-Error "ไม่มีไฟล์ใน $Source"
}

Write-Host "อัปโหลด $($files.Count) ไฟล์ ไป bucket '$Bucket' ที่ '$KeyPrefix' ..."

foreach ($f in $files) {
    # path สัมพัทธ์จาก web/
    $rel = $f.FullName.Substring((Resolve-Path $Source).Path.Length).TrimStart('\', '/')
    $key = $KeyPrefix + ($rel -replace '\\', '/')

    # กำหนด Content-Type ตามนามสกุล
    $mime = switch ([System.IO.Path]::GetExtension($f.Name).ToLower()) {
        ".html" { "text/html; charset=utf-8" }
        ".htm"  { "text/html; charset=utf-8" }
        ".js"   { "text/javascript; charset=utf-8" }
        ".mjs"  { "text/javascript; charset=utf-8" }
        ".css"  { "text/css; charset=utf-8" }
        ".json" { "application/json; charset=utf-8" }
        ".txt"  { "text/plain; charset=utf-8" }
        ".md"   { "text/markdown; charset=utf-8" }
        ".svg"  { "image/svg+xml" }
        ".png"  { "image/png" }
        ".jpg"  { "image/jpeg" }
        ".jpeg" { "image/jpeg" }
        ".gif"  { "image/gif" }
        ".webp" { "image/webp" }
        ".ico"  { "image/x-icon" }
        ".woff" { "font/woff" }
        ".woff2"{ "font/woff2" }
        ".ttf"  { "font/ttf" }
        ".otf"  { "font/otf" }
        ".pdf"  { "application/pdf" }
        ".xml"  { "application/xml; charset=utf-8" }
        default { "application/octet-stream" }
    }

    Write-Host "  -> $key  ($mime)"
    & wrangler r2 object put "$Bucket/$key" --file "$($f.FullName)" --content-type $mime

    if ($LASTEXITCODE -ne 0) {
        Write-Error "อัปโหลด $key ล้มเหลว"
    }
}

Write-Host "อัปโหลดเสร็จสมบูรณ์"
