import hashlib
import hmac
import os
import re


def hash_password(password: str) -> str:
    """PBKDF2 哈希，返回格式：pbkdf2$iterations$salt$hash。"""
    iterations = 120_000
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return f"pbkdf2${iterations}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iter_str, salt, expected = password_hash.split("$")
        if algo != "pbkdf2":
            return False
        iterations = int(iter_str)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return hmac.compare_digest(actual, expected)


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must include at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must include at least one digit."
    return True, ""
