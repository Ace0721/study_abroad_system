import unittest
from pathlib import Path

from utils.file_security import normalize_and_validate_transcript_path
from utils.security import validate_password_strength


class SecurityRulesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(__file__).resolve().parent / ".tmp_security"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for file in self.work_dir.glob("*"):
            if file.is_file():
                file.unlink(missing_ok=True)
        self.work_dir.rmdir()

    def test_password_strength(self) -> None:
        self.assertFalse(validate_password_strength("12345")[0])
        self.assertFalse(validate_password_strength("abcdef")[0])
        self.assertFalse(validate_password_strength("123456")[0])
        self.assertTrue(validate_password_strength("abc123")[0])

    def test_transcript_path_validation(self) -> None:
        file_path = self.work_dir / "score.pdf"
        file_path.write_text("x", encoding="utf-8")
        normalized = normalize_and_validate_transcript_path(str(file_path))
        self.assertTrue(normalized.endswith("score.pdf"))

    def test_transcript_path_rejects_invalid_suffix(self) -> None:
        file_path = self.work_dir / "score.exe"
        file_path.write_text("x", encoding="utf-8")
        with self.assertRaises(Exception):
            normalize_and_validate_transcript_path(str(file_path))


if __name__ == "__main__":
    unittest.main()
