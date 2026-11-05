import unittest
from unittest.mock import patch, mock_open
from s_tui.sources.cpu_freq import get_cpu_freq

class TestCpuFreq(unittest.TestCase):
    @patch('glob.glob')
    @patch('builtins.open')
    def test_get_cpu_freq_success(self, mock_file, mock_glob):
        mock_glob.return_value = ['/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq']
        mock_file.return_value = mock_open(read_data='3000000').return_value
        
        freqs = get_cpu_freq()
        self.assertEqual(freqs, [3000.0])

    @patch('glob.glob')
    @patch('builtins.open')
    def test_get_cpu_freq_error_handling(self, mock_file, mock_glob):
        mock_glob.return_value = ['/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq']
        mock_file.side_effect = IOError
        
        freqs = get_cpu_freq()
        self.assertEqual(freqs, [0.0])

if __name__ == '__main__':
    unittest.main()
