import time
import psutil
from Source import Source


class UtilSource(Source):

    def __init__(self):
        self.last_value = 0

    def get_reading(self):
        try:
            result = psutil.cpu_percent(interval=None)
        except:
            result = 0
            # logging.debug("Cpu Utilization unavailable")
        self.last_value = result            
        return result

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return True

    def get_summary(self):
        return {'Utilization': '%d %s' % (self.last_value, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Utilization'

    def get_measurement_unit(self):
        return '%'



if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
