from __future__ import annotations


_BOMS: tuple[tuple[str, str, bytes], ...] = (
    ("utf-32-be", "utf-32-be", b"\x00\x00\xfe\xff"),
    ("utf-32-le", "utf-32-le", b"\xff\xfe\x00\x00"),
    ("utf-8-sig", "utf-8", b"\xef\xbb\xbf"),
    ("utf-16-be", "utf-16-be", b"\xfe\xff"),
    ("utf-16-le", "utf-16-le", b"\xff\xfe"),
)


def detect_bom(data: bytes) -> tuple[str | None, str | None, int]:
    for encoding, bom_name, prefix in _BOMS:
        if data.startswith(prefix):
            return encoding, bom_name, len(prefix)
    return None, None, 0
