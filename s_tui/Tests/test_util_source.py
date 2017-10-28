import unittest
import sys
import os
from s_tui.Sources import UtilSource

class TestUtilSource(unittest.TestCase):

    def test_util_class(self):
        util_source = UtilSource.UtilSource()
        self.assertIsNotNone(util_source)
        reading = util_source.get_reading()
        between = reading >= 0 and reading <= 100
        self.assertTrue(between)
        self.assertEqual(util_source.get_maximum(), 100)

    def test_util_summary(self):
        util_source = UtilSource.UtilSource()
        self.assertEqual(util_source.get_source_name(), 'Utilization')

    def test_stui(self):
        os.system('s-tui -t')


if __name__ == '__main__':
    unittest.main()

