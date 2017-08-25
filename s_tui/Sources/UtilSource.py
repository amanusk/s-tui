import time
import psutil
from Source import Source


class UtilSource(Source):

    def get_reading(self):
        try:
            result = psutil.cpu_percent(interval=None)
        except:
            result = 0
            # logging.debug("Cpu Utilization unavailable")
        return result

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return True

    def get_summary(self):
        raise NotImplementedError("Get is available is not implemented")

    def get_source_name(self):
        return 'Utilization'

    def get_measurement_unit(self):
        return '%'



if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
