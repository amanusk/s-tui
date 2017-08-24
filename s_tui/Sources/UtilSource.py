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


if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
