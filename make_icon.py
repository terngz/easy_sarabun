"""สร้างไอคอนแอปจาก assets/icon.jpg  →  assets/icon.ico (หลายขนาด) + assets/icon.png

ใช้:  python make_icon.py            (อ่าน assets/icon.jpg)
      python make_icon.py my.jpg     (ระบุไฟล์เอง)
"""
import sys
from pathlib import Path

from PIL import Image

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def build_icons(src: Path, out_dir: Path) -> Path:
    img = Image.open(src).convert("RGBA")
    side = min(img.size)  # ครอปกลางให้เป็นจัตุรัส
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)

    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / "icon.png")
    ico = out_dir / "icon.ico"
    img.save(ico, format="ICO", sizes=ICO_SIZES)
    return ico


if __name__ == "__main__":
    here = Path(__file__).parent / "assets"
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "icon.jpg"
    if not src.exists():
        sys.exit(f"ไม่พบไฟล์ {src}")
    print("สร้างแล้ว:", build_icons(src, here))
