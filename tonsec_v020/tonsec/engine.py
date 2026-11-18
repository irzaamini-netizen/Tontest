import os,re,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from .parser import Function, extract_functions, line_at
from .func_parser import parse_func
from .tolk_parser import parse_tolk

EXTS={'.fc','.func','.tolk','.tact','.ts','.js','.py','.txt'}
SKIP={'.git','.venv','venv','node_modules','__pycache__','dist','build'}
SEND=[r'\bsend_raw_message\s*\(',r'\braw_reserve\s*\(',r'\bsend\s*\(']
AUTH_GUARD_IDENTITY = [
    r'\b(sender|msg_sender|context\.sender|sender_address)\b'
]
AUTH_GUARD_ROLE = [
    r'\b(owner|admin|authorized|is_authorized|role|jetton_master|minter)\b'
]
AUTH_GUARD_FUNCTION = [
    r'\b(check_signature|verify_signature|is_authorized|is_owner|only_owner|only_admin)\s*\('
]

def has_auth_guard(source):
    guards = re.finditer(
        r'\b(?:require|throw_if|throw_unless|assert)\s*\(([^;{}]*)\)',
        source,
        re.I
    )
    for match in guards:
        expr = match.group(1)
        if has(AUTH_GUARD_IDENTITY, expr) and has(AUTH_GUARD_ROLE, expr):
            return True
        if has(AUTH_GUARD_FUNCTION, expr):
            return True
    return False
