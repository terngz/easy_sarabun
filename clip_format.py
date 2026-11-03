"""Easy Sarabun - แปลงเลขใน clipboard แบบ rich (HTML / RTF) โดยคง formatting เดิม

โมดูลนี้เป็น pure Python (ไม่พึ่ง Windows) จึงทดสอบแยกได้
"""
import re

from engine import get_converter

THAI_ZERO = 0x0E50  # ๐
THAI_NINE = 0x0E59  # ๙

# ───────────────────────── HTML ─────────────────────────
_HTML_TOKEN = re.compile(
    r"(?P<skip><!--.*?-->|<style\b.*?</style\s*>|<script\b.*?</script\s*>|<[^>]*>)"
    r"|(?P<ent>&#[xX]?[0-9A-Fa-f]+;|&\w+;)"
    r"|(?P<text>[^<&]+|[<&])",
    re.S | re.I,
)
_NUM_ENTITY = re.compile(r"&#(x?)([0-9a-fA-F]+);", re.I)


def convert_html_text(html: str, reverse: bool = False) -> str:
    """แปลงเฉพาะ 'ข้อความ' ไม่แตะ tag / attribute / style / entity"""
    conv = get_converter(reverse)

    def repl(m: re.Match) -> str:
        ent = m.group("ent")
        if ent:
            if reverse:
                mm = _NUM_ENTITY.fullmatch(ent)
                if mm:
                    code = int(mm.group(2), 16 if mm.group(1) else 10)
                    if THAI_ZERO <= code <= THAI_NINE:
                        return str(code - THAI_ZERO)
            return ent
        text = m.group("text")
        return conv(text) if text else m.group(0)

    return _HTML_TOKEN.sub(repl, html)


def convert_cf_html(data: bytes, reverse: bool = False) -> bytes:
    """แปลงข้อมูลฟอร์แมต 'HTML Format' ของ Windows clipboard
    แปลงเฉพาะช่วง StartFragment..EndFragment แล้วคำนวณ offset ใน header ใหม่"""
    data = data.rstrip(b"\x00")
    head = data[:400]

    def offset(name: str):
        m = re.search(rb"%s:(\d+)" % name.encode(), head)
        return int(m.group(1)) if m else None

    sf, ef, eh = offset("StartFragment"), offset("EndFragment"), offset("EndHTML")
    if sf is None or ef is None or not (0 < sf <= ef <= len(data)):
        return data
    try:
        frag = data[sf:ef].decode("utf-8")
    except UnicodeDecodeError:
        return data

    new = convert_html_text(frag, reverse).encode("utf-8")
    delta = len(new) - (ef - sf)
    if delta == 0 and new == data[sf:ef]:
        return data

    def patch(name: str, value: int, blob: bytes) -> bytes:
        return re.sub(
            rb"(%s:)(\d+)" % name.encode(),
            lambda m: m.group(1) + str(value).zfill(len(m.group(2))).encode(),
            blob, count=1,
        )

    head_new = patch("EndFragment", ef + delta, data[:sf])
    if eh is not None:
        head_new = patch("EndHTML", eh + delta, head_new)
    return head_new + new + data[ef:]


# ───────────────────────── RTF ─────────────────────────
_RTF_TOKEN = re.compile(
    r"(?P<uni>\\u(?P<n>-?\d+) ?(?P<fb>\\'[0-9a-fA-F]{2}|[^\\{}\r\n])?)"
    r"|(?P<hex>\\'(?P<h>[0-9a-fA-F]{2}))"
    r"|(?P<word>\\(?P<w>[A-Za-z]+)(?P<p>-?\d+)?(?P<sp> )?)"
    r"|(?P<sym>\\[^A-Za-z])"
    r"|(?P<open>\{)|(?P<close>\})"
    r"|(?P<text>[^\\{}]+)"
)
# destination ที่ไม่ใช่เนื้อหา (ฟอนต์, สี, สไตล์, รูป ฯลฯ) ห้ามแตะตัวเลข
_RTF_SKIP = {
    "fonttbl", "colortbl", "stylesheet", "info", "listtable", "listoverridetable",
    "rsidtbl", "themedata", "datastore", "colorschememapping", "latentstyles",
    "pict", "object", "fldinst", "generator", "bin",
}


def convert_rtf(data: bytes, reverse: bool = False) -> bytes:
    rtf = data.rstrip(b"\x00").decode("latin-1")
    cp874 = "\\ansicpg874" in rtf
    out: list[str] = []
    stack: list[bool] = []
    skip = False
    need_delim = False  # control word ก่อนหน้าไม่มี space คั่น

    def emit_digit(d: str):
        nonlocal need_delim
        out.append((" " if need_delim else "") + d)
        need_delim = False

    for m in _RTF_TOKEN.finditer(rtf):
        if m.group("open"):
            stack.append(skip)
            out.append("{")
            need_delim = False
        elif m.group("close"):
            skip = stack.pop() if stack else False
            out.append("}")
            need_delim = False
        elif m.group("uni"):
            n = int(m.group("n"))
            n = n + 65536 if n < 0 else n
            if reverse and not skip and THAI_ZERO <= n <= THAI_NINE:
                emit_digit(str(n - THAI_ZERO))
            else:
                out.append(m.group(0))
                need_delim = False
        elif m.group("hex"):
            h = int(m.group("h"), 16)
            if reverse and cp874 and not skip and 0xF0 <= h <= 0xF9:
                emit_digit(str(h - 0xF0))
            else:
                out.append(m.group(0))
                need_delim = False
        elif m.group("word"):
            if m.group("w") in _RTF_SKIP:
                skip = True
            out.append(m.group(0))
            need_delim = m.group("sp") is None
        elif m.group("sym"):
            if m.group("sym") == "\\*":
                skip = True
            out.append(m.group(0))
            need_delim = False
        else:  # text
            text = m.group("text")
            if skip or reverse:
                out.append(text)
            else:
                out.append(re.sub(r"\d", lambda d: "\\u%d?" % (THAI_ZERO + int(d.group())), text))
            need_delim = False

    return "".join(out).encode("latin-1", errors="replace")


# ───────────────────────── Payload ─────────────────────────
def convert_payload(payload: dict, reverse: bool = False) -> dict:
    """payload = {"text": str, "html": bytes, "rtf": bytes}  (key ไหนไม่มีก็ข้าม)"""
    out = {}
    if payload.get("text"):
        out["text"] = get_converter(reverse)(payload["text"])
    if payload.get("html"):
        out["html"] = convert_cf_html(payload["html"], reverse)
    if payload.get("rtf"):
        out["rtf"] = convert_rtf(payload["rtf"], reverse)
    return out
