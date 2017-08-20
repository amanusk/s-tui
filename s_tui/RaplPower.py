import os
import time

class RaplPower:

	intel_rapl_folder = '/sys/class/powercap/intel-rapl/'

	MICRO_JAUL_IN_JAUL = 1000000.0

	def __init__(self, package_number = 0):
		self.package_number = package_number
		self.intel_rapl_package_energy_file = os.path.join(self.intel_rapl_folder, 'intel-rapl:%d'%package_number, 'energy_uj')
		
		if (not os.path.exists(self.intel_rapl_package_energy_file)):
			self.is_available = False
			return

		self.is_available = True
		self.last_measurement_time = time.time()
		self.last_measurement_value = self.read_power_measurement_file()
	
	def read_power_measurement_file(self):
		if not self.is_available:
			return -1
		file = open(self.intel_rapl_package_energy_file)
		current_measurement_value = file.read()
		file.close()
		return float(current_measurement_value)


	def get_power_usage(self):
		if not self.is_available:
			return -1
		current_measurement_value = self.read_power_measurement_file()
		current_measurement_time = time.time()

		jaul_used = (current_measurement_value - self.last_measurement_value) / self.MICRO_JAUL_IN_JAUL
		seconds_passed = current_measurement_time - self.last_measurement_time
		jaul_used_per_second = jaul_used / seconds_passed

		self.last_measurement_value = current_measurement_value
		self.last_measurement_time = current_measurement_time	
		return jaul_used_per_second

	def get_is_available(self):
		return self.is_available

if '__main__' == __name__:
    rapl = RaplPower()
    while True:
	print(rapl.get_power_usage())
	time.sleep(2)
