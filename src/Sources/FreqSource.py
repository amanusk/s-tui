import psutil
import os
import re
import subprocess
from Source import Source
from HelperFunctions import read_msr
from HelperFunctions import TURBO_MSR

import logging
logger = logging.getLogger(__name__)

class FreqSource(Source):

    def __init__(self, is_admin):
        self.is_admin = is_admin

        self.top_freq = 100
        self.turbo_freq = False
        self.last_freq = 0
        self.samples_taken = 0
        self.WAIT_SAMPLES = 5
        self.perf_lost = 0
        self.max_perf_lost = 0
        # Top frequency in case using Intel Turbo Boost
        if self.is_admin:
            try:
                num_cpus = psutil.cpu_count()
                logging.debug("num cpus " + str(num_cpus))
                available_freq = read_msr(TURBO_MSR, 0)
                logging.debug(available_freq)
                max_turbo_msr = num_cpus
                # The MSR only holds 8 values. Number of cores could be higher
                if num_cpus > 8:
                    max_turbo_msr = 8
                self.top_freq = float(available_freq[max_turbo_msr - 1] * 100)
                self.turbo_freq = True
            except (IOError, OSError) as e:
                logging.debug(e.message)

        if self.top_freq == 100:
            try:
                self.top_freq = psutil.cpu_freq().max
                self.turbo_freq = False
            except:
                logging.debug("Max freq from psutil not available")
                try:
                    cmd = "lscpu | grep 'CPU max MHz'"
                    ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                    output = ps.communicate()[0]
                    self.top_freq = float(re.findall("\d+\.\d+", output)[0])
                except:
                    logging.debug("Max frequency from lscpu not available")
                    logging.debug("CPU top freqency N/A")
                    self.top_freq = 100




    def get_reading(self):
        """Update CPU frequency data"""
        def get_avarage_cpu_freq():
            with open("/proc/cpuinfo") as cpuinfo:
                cores_freq = []
                for line in cpuinfo:
                    if "cpu MHz" in line:
                        core_freq = re.findall("\d+\.\d+", line)
                        cores_freq += core_freq
            return round(reduce(lambda x, y: float(x) + float(y), cores_freq) / len(cores_freq), 1)

        try:
            cur_freq = int(psutil.cpu_freq().current)
        except:
            cur_freq = 0
            try:
                cur_freq = get_avarage_cpu_freq()
            except:
                cur_freq = 0
                logging.debug("Frequency unavailable")

        self.samples_taken += 1

        # Here is where we need to generate the max frequency lost

        if self.is_admin and self.samples_taken > self.WAIT_SAMPLES:
            self.perf_lost = int(self.top_freq) - int(cur_freq)
            if self.top_freq != 0:
                self.perf_lost = (round(float(self.perf_lost) / float(self.top_freq) * 100, 1))
            else:
                self.perf_lost = 0
            if self.perf_lost > self.max_perf_lost:
                self.max_perf_lost = self.perf_lost
        elif not self.is_admin:
            self.max_perf_lost = 0

        self.last_freq = cur_freq
        return cur_freq

    def get_maximum(self):
        return self.top_freq

    def get_is_available(self):
        return True

    def get_summary(self):
        if self.is_admin:
            return {'Cur Freq': '%d %s' % (self.last_freq, self.get_measurement_unit())
                    , 'Perf Lost': '%d %s' % (self.max_perf_lost, '%')
                    , 'Top Freq': '%d %s' % (self.top_freq, self.get_measurement_unit())}
        else:
            return {'Cur Freq': '%d %s' % (self.last_freq, self.get_measurement_unit())
                    , 'Perf Lost': '%d %s' % (self.max_perf_lost, '(N/A)')
                    , 'Top Freq': '%d %s' % (self.top_freq, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Frequency'

    def get_measurement_unit(self):
        return 'MHz'
