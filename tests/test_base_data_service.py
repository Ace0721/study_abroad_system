import unittest

from utils.seed_defs import UNIVERSITY_SEED_DATA


class BaseDataSeedShapeTestCase(unittest.TestCase):
    def test_seed_has_three_universities_and_each_has_three_majors(self) -> None:
        self.assertGreaterEqual(len(UNIVERSITY_SEED_DATA), 3)
        for item in UNIVERSITY_SEED_DATA:
            self.assertEqual(len(item), 4)
            majors = item[3]
            self.assertGreaterEqual(len(majors), 3)


if __name__ == "__main__":
    unittest.main()
