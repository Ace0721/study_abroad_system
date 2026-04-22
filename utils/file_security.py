from pathlib import Path

from utils.exceptions import BusinessRuleError


ALLOWED_TRANSCRIPT_SUFFIXES = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
}


def normalize_and_validate_transcript_path(raw_path: str) -> str:
    text = (raw_path or "").strip()
    text = text.strip('"').strip("'")
    if not text:
        raise BusinessRuleError("Transcript path is required.")

    path = Path(text)
    normalized = path if path.is_absolute() else path.resolve(strict=False)
    normalized_str = str(normalized)

    if normalized_str.startswith("\\\\"):
        raise BusinessRuleError("Network paths are not allowed for transcript files.")
    if len(normalized_str) > 255:
        raise BusinessRuleError("Transcript path is too long.")

    suffix = normalized.suffix.lower()
    if suffix not in ALLOWED_TRANSCRIPT_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_TRANSCRIPT_SUFFIXES))
        raise BusinessRuleError(f"Transcript file type is not allowed. Allowed: {allowed}")

    if not normalized.exists() or not normalized.is_file():
        raise BusinessRuleError("Transcript file does not exist.")
    return normalized_str
