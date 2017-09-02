import os
import time

from Source import Source

class RaplPowerSource(Source):

    intel_rapl_folder = '/sys/class/powercap/intel-rapl/'

    MICRO_JOULE_IN_JOULE = 1000000.0

    def __init__(self, package_number = 0):
        self.package_number = package_number
        self.intel_rapl_package_energy_file = os.path.join(self.intel_rapl_folder, 'intel-rapl:%d'%package_number, 'energy_uj')
        self.intel_rapl_package_max_energy_file = os.path.join(self.intel_rapl_folder, 'intel-rapl:%d'%package_number, 'constraint_0_max_power_uw')
        if (not os.path.exists(self.intel_rapl_package_energy_file) or not os.path.exists(self.intel_rapl_package_max_energy_file)):
            self.is_available = False
            self.last_measurement_time = 0
            self.last_measurement_value = 0
            self.max_power = 0
            self.last_watts = 0
            return

        self.is_available = True
        self.last_measurement_time = time.time()
        self.last_measurement_value = self.read_power_measurement_file()
        #self.max_power = self.read_max_power_file() / self.MICRO_JOULE_IN_JOULE
        self.max_power = 0
        self.last_watts = 0

        self.update()

    def read_measurement(self, file_path):
        try:
            with open(file_path) as f:
                value = f.read()
                return float(value)
        except:
            return 0

    def read_max_power_file(self):
        if not self.is_available:
            return -1
        return float(self.read_measurement(self.intel_rapl_package_max_energy_file))

    def read_power_measurement_file(self):
        if not self.is_available:
            return -1
        return float(self.read_measurement(self.intel_rapl_package_energy_file))

    def get_power_usage(self):
        if not self.is_available:
            return -1
        current_measurement_value = self.read_power_measurement_file()
        current_measurement_time = time.time()

        joule_used = (current_measurement_value - self.last_measurement_value) / self.MICRO_JOULE_IN_JOULE
        seconds_passed = current_measurement_time - self.last_measurement_time
        watts_used = joule_used / seconds_passed

        self.last_measurement_value = current_measurement_value
        self.last_measurement_time = current_measurement_time
        self.last_watts = watts_used
        try:
            if int(watts_used) > int(self.max_power):
                self.max_power = watts_used
        except:
            self.max_power = 0
        return watts_used

    # Source super class implementation
    def get_is_available(self):
        return self.is_available

    def update(self):
        self.get_power_usage()

    def get_reading(self):
        return self.last_watts

    def get_maximum(self):
        return self.max_power

    def reset(self):
        self.max_power = 1
        self.last_watts = 1

    def get_summary(self):
        return {'Cur Power': '%.1f %s' % (self.last_watts, self.get_measurement_unit())
                , 'Max Power': '%.1f %s' % (self.max_power, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Power'

    def get_measurement_unit(self):
        return 'W'


if '__main__' == __name__:
    rapl = RaplPower()
    while True:
        print(rapl.get_power_usage())
        time.sleep(2)
