import time
import psutil
from Source import Source

import logging
logger = logging.getLogger(__name__)


class UtilSource(Source):

    def __init__(self):
        self.last_freq = 0
        self.update()

    def update(self):
        result = 0
        try:
            result = float(psutil.cpu_percent(interval=0.0))
        except:
            result = 0
            logging.debug("Cpu Utilization unavailable")

        self.last_freq = float(result)
        logging.info("Utilization recorded " + str(self.last_freq))

    def get_reading(self):
        return self.last_freq

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return True

    def get_summary(self):
        return {'Utilization': '%.1f %s' % (self.last_freq, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Utilization'

    def get_measurement_unit(self):
        return '%'



if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
