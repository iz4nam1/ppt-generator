"""
utils/security.py
==================
Security utilities — sanitization, validation, hashing.
"""

import hashlib
import re
from pathlib import Path
from app.config import TEXT_EXTENSIONS, MAX_DESCRIPTION_LEN


def sanitize_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r'[^\w\-_\.]', '_', name)
    return name[:100]


def sanitize_text(text: str, max_len: int = 200) -> str:
    return re.sub(r'[\x00-\x1f\x7f<>]', '', text[:max_len]).strip()


def sanitize_description(text: str) -> str:
    text = text[:MAX_DESCRIPTION_LEN]
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text).strip()


def validate_magic(data: bytes, filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    if ext == ".pptx":       return data[:4] == b"PK\x03\x04"
    if ext == ".pdf":        return data[:4] == b"%PDF"
    if ext in {".jpg",".jpeg"}: return data[:3] == b"\xff\xd8\xff"
    if ext == ".png":        return data[:4] == b"\x89PNG"
    if ext in TEXT_EXTENSIONS:
        try: data[:512].decode("utf-8"); return True
        except: return False
    return True


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def validate_email(email: str) -> bool:
    return bool(re.match(
        r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email
    ))
