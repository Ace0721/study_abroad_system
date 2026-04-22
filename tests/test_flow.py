import unittest

from utils.security import hash_password, verify_password


class SecurityTestCase(unittest.TestCase):
    def test_password_hash_and_verify(self) -> None:
        hashed = hash_password("123456")
        self.assertTrue(verify_password("123456", hashed))
        self.assertFalse(verify_password("wrong", hashed))


if __name__ == "__main__":
    unittest.main()

