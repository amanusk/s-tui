import psutil
import os
import re
import subprocess

import logging
logger = logging.getLogger(__name__)

class GlobalData:

    def __init__(self, is_admin):
        self.is_admin = is_admin
        self.num_cpus = 1
        try:
            self.num_cpus = psutil.cpu_count()
            logging.info("num cpus " + str(self.num_cpus))
        except (IOError, OSError) as e:
            logging.debug(e.message)
