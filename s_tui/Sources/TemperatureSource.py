
import psutil
import os
from Source import Source

import logging
logger = logging.getLogger(__name__)


class TemperatureSource(Source):

    THRESHOLD_TEMP = 80
    DEGREE_SIGN = u'\N{DEGREE SIGN}'

    def __init__(self):
        self.max_temp = 0
        self.measurement_unit = 'C'
        self.last_temp = 0;

    def update(self):
        """
        Read the latest Temperature reading.
        Reading for temperature might be different between systems
        Support for additional systems can be added here
        """
        last_value = 0
        # NOTE: Negative values might not be supported

        # Temperature on most common systems is in coretemp
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['coretemp'][0].current
            except:
                last_value = 0
        # Support for Ryzen 7 + asus
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['it8655'][0].current
            except:
                last_value = 0
        # Support for specific systems
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['it8622'][0].current
            except:
                last_value = 0
        # Support for specific systems
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['it8721'][0].current
            except:
                last_value = 0
        # Raspberry pi 3 running Ubuntu 16.04
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
            except:
                last_value = 0
        # Raspberry pi + raspiban CPU temp
        if last_value <= 0:
            try:
                last_value = os.popen('cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
                logging.info("Recorded temp " + last_value)
                last_value = int(last_value) / 1000
            except:
                last_value = 0
        # Fall back for most single processor systems
        # Take the first value of the first processor
        if last_value <= 0:
            try:
                temperatures = psutil.sensors_temperatures()
                chips = list(temperatures.keys())
                last_value = temperatures[chips[0]][0].current
            except:
                last_value = 0

        # If not relevant sensor found, do not register temperature
        if last_value <= 0:
            logging.debug("Temperature sensor unavailable")

        # self.cpu_temp = self.append_latest_value(self.cpu_temp, last_value)
        # Update max temp
        try:
            if int(last_value) > int(self.max_temp):
                self.max_temp = last_value
        except:
            self.max_temp = 0

        # Update current temp
        #if last_value is None:
        #    last_value = 0
        #    self.overheat = False
        #if last_value >= self.THRESHOLD_TEMP:
        #    self.overheat = True
        #    self.overheat_detected = True
        #else:
        #    self.overheat = False

        self.last_temp = last_value

    def get_reading(self):
        return self.last_temp

    def get_maximum(self):
        return self.max_temp

    def get_is_available(self):
        return True

    def get_edge_triggered(self):
        return self.last_temp > self.THRESHOLD_TEMP

    def get_max_triggered(self):
        return self.max_temp > self.THRESHOLD_TEMP

    def get_summary(self):
        return {'Cur Temp': '%.1f %s' % (self.last_temp, self.get_measurement_unit())
                , 'Max Temp': '%.1f %s' % (self.max_temp, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Temperature'

    def get_measurement_unit(self):
        return self.measurement_unit

