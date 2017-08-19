import os

class RaplPower:

	intel_rapl_folder = '/sys/class/powercap/intel-rapl/'

	def __init__(self, package_number = 0, method = 'sysfs'):
		self.package_number = package_number
		self.intel_rapl_package_energy_file = os.path.join(self.intel_rapl_folder, 'intel-rapl:%d'%package_number, 'energy_uj')
		
		# if (not os.path.exists(self.intel_rapl_package_energy_file)):

	def start(self):
		if (not os.path.exists(self.intel_rapl_package_energy_file)):
			return False
		
		
