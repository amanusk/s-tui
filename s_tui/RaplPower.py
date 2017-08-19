import os
import time

class RaplPower:

	intel_rapl_folder = '/sys/class/powercap/intel-rapl/'

	MICRO_JAUL_IN_JAUL = 1,000,000

	def __init__(self, package_number = 0):
		self.package_number = package_number
		self.intel_rapl_package_energy_file = os.path.join(self.intel_rapl_folder, 'intel-rapl:%d'%package_number, 'energy_uj')
		
		# if (not os.path.exists(self.intel_rapl_package_energy_file)):
	# this shouldn't be a startable class
	def start(self):
		if (not os.path.exists(self.intel_rapl_package_energy_file)):
			return False

		self.last_measurement_time = time.time()
		self.last_measurement_value = read_power_measurement_file()

	def read_power_measurement_file(self):
		file = open(self.intel_rapl_package_energy_file)
		current_measurement_value = file.read()
		close(file)
		return current_measurement_value

	def get_power_usage(self):
		current_measurement_value = read_power_measurement_file()
		current_measurement_time = time.time()

		jaul_used = (current_measurement_value - self.last_measurement_value) / MICRO_JAUL_IN_JAUL
		seconds_passed = current_measurement_time - self.last_measurement_time
		jaul_used_per_second = jaul_used / seconds_passed

		return jaul_used_per_second