import unittest
from s_tui.Sources import UtilSource


class TestUtilSource(unittest.TestCase):
    def test_util_class(self):
        util_source = UtilSource.UtilSource()
        self.assertIsNotNone(util_source)

    def test_util_summary(self):
        util_source = UtilSource.UtilSource()
        self.assertEqual(util_source.get_source_name(), 'Util')


if __name__ == '__main__':
    unittest.main()
