import psutil
from Source import Source
from HelperFunctions import get_avarage_cpu_freq

class FreqSource(Source):

    def __init__(self, is_admin):
        self.is_admin = is_admin

        self.top_freq = 100
        self.turbo_freq = False

        # Top frequency in case using Intel Turbo Boost
        if self.is_admin:
            try:
                num_cpus = psutil.cpu_count()
                logging.info("num cpus " + str(num_cpus))
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
                try:
                    cmd = "lscpu | grep 'CPU max MHz'"
                    ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                    output = ps.communicate()[0]
                    self.top_freq = float(re.findall("\d+\.\d+", output)[0])
                except:
                    # logging.debug("CPU top freqency N/A")
                    self.top_freq = 100



    def get_reading(self):
        """Update CPU frequency data"""
        try:
            cur_freq = int(psutil.cpu_freq().current)
        except:
            cur_freq = 0
            try:
                cur_freq = get_avarage_cpu_freq()
            except:
                cur_freq = 0
                # logging.debug("Frequency unavailable")

        if self.is_admin and self.samples_taken > self.WAIT_SAMPLES:
            self.perf_lost = int(self.top_freq) - int(self.cur_freq)
            if self.top_freq != 0:
                self.perf_lost = (round(float(self.perf_lost) / float(self.top_freq) * 100, 1))
            else:
                self.perf_lost = 0
            if self.perf_lost > self.max_perf_lost:
                self.max_perf_lost = self.perf_lost
        elif not self.is_admin:
            self.max_perf_lost = "N/A (no root)"
        return cur_freq

    def get_maximum(self):
        return self.top_freq

    def get_is_available(self):
        return True

    def get_summary(self):
        raise NotImplementedError("Get is available is not implemented")

    def get_source_name(self):
        return 'Frequency'

    def get_measurement_unit(self):
        return 'MHz'
