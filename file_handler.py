"""Easy Sarabun - แปลงเลขในไฟล์เอกสารหลายชนิด (คง formatting เดิม)

รองรับตรง ๆ (ไม่ต้องมีโปรแกรมอื่น):
    Word .docx/.docm · PowerPoint .pptx/.pptm · Excel .xlsx/.xlsm
    OpenDocument .odt/.odp/.ods · .rtf · .txt/.md/.csv · .html/.htm
รองรับผ่านการแปลงไฟล์ (ต้องมี MS Office หรือ LibreOffice ในเครื่อง):
    .doc → .docx · .ppt → .pptx · .xls → .xlsx
"""
from __future__ import annotations

import codecs
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from clip_format import convert_html_text, convert_rtf
from engine import get_converter

OOXML = {".docx": "word/", ".docm": "word/", ".pptx": "ppt/", ".pptm": "ppt/",
         ".xlsx": "xl/", ".xlsm": "xl/"}
ODF = {".odt", ".ods", ".odp"}
RTF = {".rtf"}
TEXT = {".txt", ".md", ".csv"}
HTML = {".html", ".htm"}
LEGACY = {".doc": ".docx", ".ppt": ".pptx", ".xls": ".xlsx"}

SUPPORTED = set(OOXML) | ODF | RTF | TEXT | HTML | set(LEGACY)
FILETYPES = [
    ("เอกสารที่รองรับทั้งหมด", tuple(f"*{e}" for e in sorted(SUPPORTED))),
    ("Word", ("*.docx", "*.doc", "*.odt", "*.rtf")),
    ("PowerPoint", ("*.pptx", "*.ppt", "*.odp")),
    ("Excel", ("*.xlsx", "*.xls", "*.ods", "*.csv")),
    ("ข้อความ / เว็บ", ("*.txt", "*.md", "*.html", "*.htm")),
]

# ───────────── OOXML (docx / pptx / xlsx) ─────────────
# แก้เฉพาะ text node ของ <w:t> <a:t> <t> <m:t> — ไม่แตะ field code (instrText), สูตร, ค่าตัวเลขของเซลล์
_OOXML_T = re.compile(r"(<(?:[\w.-]+:)?t(?:\s[^>]*?)?(?<!/)>)([^<]*)(</(?:[\w.-]+:)?t>)")


def _convert_ooxml_part(data: bytes, reverse: bool) -> bytes:
    try:
        xml = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    new = _OOXML_T.sub(lambda m: m.group(1) + convert_html_text(m.group(2), reverse) + m.group(3), xml)
    return data if new == xml else new.encode("utf-8")


# ───────────── Excel worksheet ─────────────
# เซลล์ตัวเลข (numeric) เก็บค่าไว้ใน <v> โดยตรง ไม่มีแท็ก <t> → regex ด้านบนพลาดไป
# แก้โดยแปลงค่าใน <v> ของเฉพาะเซลล์ตัวเลข แต่ข้าม:
#   - sharedString index   : <c t="s"><v>0</v></c>  (0 คือ index ไม่ใช่ตัวเลขที่แสดง)
#   - boolean/date/error   : t="b" | t="d" | t="e"
#   - inline/str           : t="inlineStr" | t="str"
#   - cell ที่เป็นสูตร      : มี <f> (ค่าใน <v> เป็นผลลัพธ์แคช จะถูกคำนวณใหม่ทับ)
_XLSX_CELL = re.compile(r"<c\b([^>]*?)\s*>((?:(?!</c>).)*?)</c>", re.S)
_XLSX_V = re.compile(r"<v>([^<]*)</v>")


def _convert_xlsx_sheet(data: bytes, reverse: bool) -> bytes:
    try:
        xml = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    # inline string runs: <c t="inlineStr"><is><r><t>123</t></r></is></c>
    xml = _OOXML_T.sub(lambda m: m.group(1) + convert_html_text(m.group(2), reverse) + m.group(3), xml)

    conv = get_converter(reverse)

    def convert_v(m: re.Match) -> str:
        return "<v>" + conv(m.group(1)) + "</v>"

    def convert_cell(m: re.Match) -> str:
        attrs, body = m.group(1), m.group(2)
        tm = re.search(r'\bt="([^"]+)"', attrs)
        if tm and tm.group(1) in ("s", "b", "d", "e", "inlineStr", "str"):
            return m.group(0)  # ไม่ใช่เซลล์ตัวเลข
        if "<f" in body:
            return m.group(0)  # เซลล์สูตร — ไม่แตะ (กันเลขซ้ำ/เพี้ยนจาก recalculation)
        return "<c" + attrs + ">" + _XLSX_V.sub(convert_v, body) + "</c>"

    new = _XLSX_CELL.sub(convert_cell, xml)
    return data if new == xml else new.encode("utf-8")


def _transform_ooxml(name: str, data: bytes, ext: str, reverse: bool) -> bytes:
    if ext in (".xlsx", ".xlsm") and re.match(r"xl/worksheets/[^/]+\.xml$", name):
        return _convert_xlsx_sheet(data, reverse)
    prefix = OOXML[ext]
    if name.startswith(prefix) and name.endswith(".xml"):
        return _convert_ooxml_part(data, reverse)
    return data


# ───────────── OpenDocument ─────────────
_ODF_SKIP = {"date", "creator", "date-string", "initial-creator", "creator-initials",
             "binary-data", "script", "print-date", "printed-by"}
_ODF_PARTS = {"content.xml", "styles.xml"}


def _convert_odf_part(data: bytes, reverse: bool) -> bytes:
    conv = get_converter(reverse)
    root = etree.fromstring(data, etree.XMLParser(huge_tree=True, resolve_entities=False))
    for el in root.iter():
        is_element = isinstance(el.tag, str)
        if is_element and el.text and el.tag.rsplit("}", 1)[-1] not in _ODF_SKIP:
            el.text = conv(el.text)
        if el.tail:
            el.tail = conv(el.tail)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


# ───────────── zip rewrite (คง order / compression / mimetype ของต้นฉบับ) ─────────────
def _rewrite_zip(src: Path, dst: Path, transform) -> None:
    try:
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, transform(item.filename, zin.read(item.filename)))
    except Exception:
        dst.unlink(missing_ok=True)
        raise


# ───────────── text / html ─────────────
def _decode_text(data: bytes) -> tuple[str, str]:
    if data.startswith(codecs.BOM_UTF8):
        return data[3:].decode("utf-8"), "utf-8-sig"
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp874"), "cp874"  # ไฟล์ไทยเก่า (Windows-874)


# ───────────── .doc / .ppt / .xls → OOXML ─────────────
def _find_soffice() -> str | None:
    found = shutil.which("soffice")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base and (p := Path(base) / "LibreOffice" / "program" / "soffice.exe").exists():
            return str(p)
    return None


def _convert_legacy(src: Path, target_ext: str, workdir: Path) -> Path:
    out = workdir / (src.stem + target_ext)

    soffice = _find_soffice()
    if soffice:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            [soffice, "--headless", "--convert-to", target_ext.lstrip("."), "--outdir", str(workdir), str(src)],
            check=False, timeout=180, creationflags=flags, capture_output=True,
        )
        if out.exists():
            return out

    try:  # MS Office ผ่าน COM (เปิดอินสแตนซ์แยก ไม่ยุ่งกับไฟล์ที่เปิดอยู่)
        import pythoncom
        import win32com.client as wc
    except ImportError:
        raise RuntimeError("ไฟล์ชนิดนี้ต้องมี Microsoft Office หรือ LibreOffice ในเครื่อง")

    pythoncom.CoInitialize()
    app = None
    try:
        if target_ext == ".docx":
            app = wc.DispatchEx("Word.Application")
            app.Visible, app.DisplayAlerts = False, 0
            doc = app.Documents.Open(str(src), ReadOnly=True, AddToRecentFiles=False)
            doc.SaveAs2(str(out), FileFormat=16)  # wdFormatXMLDocument
            doc.Close(False)
        elif target_ext == ".xlsx":
            app = wc.DispatchEx("Excel.Application")
            app.Visible, app.DisplayAlerts = False, False
            wb = app.Workbooks.Open(str(src), ReadOnly=True)
            wb.SaveAs(str(out), FileFormat=51)  # xlOpenXMLWorkbook
            wb.Close(False)
        else:
            app = wc.DispatchEx("PowerPoint.Application")
            pres = app.Presentations.Open(str(src), ReadOnly=True, WithWindow=False)
            pres.SaveAs(str(out), 24)  # ppSaveAsOpenXMLPresentation
            pres.Close()
    except Exception as e:
        raise RuntimeError(f"แปลง {src.suffix} ไม่สำเร็จ (ต้องมี MS Office หรือ LibreOffice): {e}")
    finally:
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()

    if not out.exists():
        raise RuntimeError(f"แปลง {src.suffix} ไม่สำเร็จ")
    return out


# ───────────── public API ─────────────
def process_file(file_path: str, reverse: bool = False) -> str:
    """แปลงเลขทั้งไฟล์ แล้วบันทึกเป็นไฟล์ใหม่ข้างไฟล์เดิม คืนค่า path ไฟล์ใหม่

    reverse=False : 0-9 -> ๐-๙  (บันทึกเป็น *_thai.*)
    reverse=True  : ๐-๙ -> 0-9  (บันทึกเป็น *_arabic.*)
    """
    src = Path(file_path)
    ext = src.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"ไม่รองรับไฟล์ชนิด {ext or '(ไม่มีนามสกุล)'}")

    tmpdir = None
    try:
        if ext in LEGACY:
            tmpdir = Path(tempfile.mkdtemp(prefix="easy_sarabun_"))
            src, ext = _convert_legacy(src, LEGACY[ext], tmpdir), LEGACY[ext]
            dst_dir = Path(file_path).parent
            stem = Path(file_path).stem
        else:
            dst_dir, stem = src.parent, src.stem

        dst = dst_dir / f"{stem}{'_arabic' if reverse else '_thai'}{ext}"
        conv = get_converter(reverse)

        if ext in OOXML:
            _rewrite_zip(src, dst, lambda name, data: _transform_ooxml(name, data, ext, reverse))
        elif ext in ODF:
            _rewrite_zip(src, dst, lambda name, data: (
                _convert_odf_part(data, reverse) if name in _ODF_PARTS else data))
        elif ext in RTF:
            dst.write_bytes(convert_rtf(src.read_bytes(), reverse))
        else:  # txt / md / csv / html
            text, enc = _decode_text(src.read_bytes())
            text = convert_html_text(text, reverse) if ext in HTML else conv(text)
            dst.write_bytes(text.encode(enc))
        return str(dst)
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
