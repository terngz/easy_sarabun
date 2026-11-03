"""Easy Sarabun - digit conversion core."""

ARABIC_TO_THAI = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def to_thai(text: str) -> str:
    """0-9 -> ๐-๙"""
    return text.translate(ARABIC_TO_THAI) if text else ""


def to_arabic(text: str) -> str:
    """๐-๙ -> 0-9"""
    return text.translate(THAI_TO_ARABIC) if text else ""


def get_converter(reverse: bool = False):
    """reverse=False: อารบิก -> ไทย | reverse=True: ไทย -> อารบิก"""
    return to_arabic if reverse else to_thai
