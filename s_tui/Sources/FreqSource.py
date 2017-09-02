import psutil
import os
import re
import subprocess
from Source import Source
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

TURBO_MSR = 429

def read_msr(msr, cpu=0):
    """
    reads the msr number given from the file /dev/cpu/0/msr
    Reuturns the value
    """
    if not os.path.exists("/dev/cpu/0/msr"):
        try:
            os.system("/sbin/modprobe msr")
            logging.debug("Ran modprobe sucessfully")
        except:
            pass
            return None
    msr_file = '/dev/cpu/%d/msr' % (cpu,)
    try:
        with open(msr_file, 'r') as f:
            f.seek(msr)
            read_res = f.read(8)
        s_decoded = [ord(c) for c in read_res]
        return s_decoded
    except IOError as e:
        e.message = e.message + "Unable to read file " + msr_file
        raise e
    except OSError as e:
        e.message = e.message + "File " + msr_file + " does not exist"
        raise e

class FreqSource(Source):

    def __init__(self, is_admin):
        self.is_admin = is_admin
        self.is_avaiable = True

        self.top_freq = 0
        self.turbo_freq = False
        self.last_freq = 0
        self.samples_taken = 0
        self.WAIT_SAMPLES = 5
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.stress_started = False
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
                freq = float(available_freq[max_turbo_msr - 1] * 100)
                if freq > 0:
                    self.top_freq = freq
                    self.turbo_freq = True
            except Exception as e:
                logging.debug(e.message)

        if self.turbo_freq == False:
            try:
                self.top_freq = psutil.cpu_freq().max

            except:
                logging.debug("Max freq from psutil not available")
                try:
                    cmd = "lscpu | grep 'CPU MHz'"
                    ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                    output = ps.communicate()[0]
                    self.top_freq = float(re.findall("\d+\.\d+", output)[0])
                    if self.top_freq <= 0:
                        cmd = "lscpu | grep 'CPU * MHz'"
                        ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                        output = ps.communicate()[0]
                        self.top_freq = float(re.findall("\d+\.\d+", output)[0])
                except:
                    logging.debug("Max frequency from lscpu not available")
                    logging.debug("CPU top freqency N/A")

        self.update()
        # If top freq not available, take the current as top
        if self.last_freq >= 0 and self.top_freq <=0:
            self.top_freq = self.last_freq
        if self.last_freq <= 0:
            self.is_avaiable = False


    def update(self):
        """Update CPU frequency data"""
        def get_avarage_cpu_freq():
            with open("/proc/cpuinfo") as cpuinfo:
                cores_freq = []
                for line in cpuinfo:
                    if "cpu MHz" in line:
                        core_freq = re.findall("\d+\.\d+", line)
                        cores_freq += core_freq
            return round(sum(float(x) for x in cores_freq) / len(cores_freq), 1)

        try:
            cur_freq = int(psutil.cpu_freq().current)
        except:
            cur_freq = 0
            try:
                cur_freq = get_avarage_cpu_freq()
            except:
                cur_freq = 0
                logging.debug("Frequency unavailable")

        if self.stress_started:
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

    def get_reading(self):
        return self.last_freq

    def get_maximum(self):
        return self.top_freq

    def get_is_available(self):
        return self.is_avaiable

    def reset(self):
        self.max_perf_lost = 0

    def set_stress_started(self):
        self.stress_started = True

    def set_stress_stopped(self):
        self.stress_started = False
        self.samples_taken = 0

    def get_summary(self):
        if self.is_admin:
            return OrderedDict([
                    ( 'Top Freq', '%d %s' % (self.top_freq, self.get_measurement_unit()))
                    , ('Cur Freq', '%.1f %s' % (self.last_freq, self.get_measurement_unit()))
                    , ('Perf Lost', '%d %s' % (self.max_perf_lost, '%'))
            ])
        else:
            return OrderedDict([
                    ( 'Top Freq', '%d %s' % (self.top_freq, self.get_measurement_unit()))
                    , ('Cur Freq', '%.1f %s' % (self.last_freq, self.get_measurement_unit()))
                    , ('Perf Lost', '%d %s' % (self.max_perf_lost, '(N/A) run sudo'))
            ])

    def get_source_name(self):
        return 'Frequency'

    def get_measurement_unit(self):
        return 'MHz'
