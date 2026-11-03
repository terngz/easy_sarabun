"""Easy Sarabun - แปลงตัวเลขในไฟล์ .docx โดยคง formatting เดิม"""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from engine import get_converter

_W_T = qn("w:t")


def _convert_tree(root, converter) -> None:
    """แปลงทุก <w:t> ใต้ root (รวมตารางซ้อน, text box, hyperlink)
    แก้เฉพาะ node ที่เปลี่ยนจริง เพื่อไม่แตะ run properties"""
    for node in root.iter(_W_T):
        if node.text:
            new = converter(node.text)
            if new != node.text:
                node.text = new


def process_docx_file(file_path: str, reverse: bool = False) -> str:
    """แปลงเลขทั้งไฟล์ แล้วบันทึกเป็นไฟล์ใหม่ข้างไฟล์เดิม คืนค่า path ไฟล์ใหม่

    reverse=False : 0-9 -> ๐-๙  (บันทึกเป็น *_thai.docx)
    reverse=True  : ๐-๙ -> 0-9  (บันทึกเป็น *_arabic.docx)
    """
    doc = Document(file_path)
    converter = get_converter(reverse)

    roots = [doc.element.body]
    seen = set()
    for section in doc.sections:
        for part in (
            section.header, section.first_page_header, section.even_page_header,
            section.footer, section.first_page_footer, section.even_page_footer,
        ):
            if part.is_linked_to_previous:
                continue
            element = part._element
            if id(element) not in seen:
                seen.add(id(element))
                roots.append(element)

    for root in roots:
        _convert_tree(root, converter)

    src = Path(file_path)
    out = src.with_name(f"{src.stem}{'_arabic' if reverse else '_thai'}{src.suffix}")
    doc.save(out)
    return str(out)
