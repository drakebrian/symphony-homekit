import logging
import os
import pyhap.loader as loader
import signal
from pyhap.accessory import Accessory
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_SENSOR
from waterfurnace.waterfurnace import WaterFurnace

ACC_NAME    = 'Thermostat' # Accessory name, can be changed here or later in HomeKit
USE_PORT    = 51826
CELSIUS     = False
SETPOINTS   = False # If True, report thermostat setpoints instead of actual readings

user = os.environ.get['SYMPHONY_USER']
pwd = os.environ.get['SYMPHONY_PWD']

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

if not user or not pwd:
    logging.error('Username or password variables not set')

try:
    wf = WaterFurnace(user, pwd)
    login = wf.login()
except Exception as ex:
    logging.error('Symphony login failed. Check username and password')

class TemperatureSensor(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        temp_service = self.add_preload_service('TemperatureSensor')
        self.temp_char = temp_service.get_characteristic('CurrentTemperature')

        temp_humidity = self.add_preload_service('HumiditySensor')
        self.humid_char = temp_humidity.get_characteristic('CurrentRelativeHumidity')

    @Accessory.run_at_interval(10)
    def run(self):
        data = wf.read()

        setpoint_temp = float(data.tstatactivesetpoint) if CELSIUS else (float(data.tstatactivesetpoint)-32) * 5/9
        room_temp = float(data.tstatroomtemp) if CELSIUS else (float(data.tstatroomtemp)-32) * 5/9

        setpoint_humidity = data.tstathumidsetpoint
        room_humidity = data.tstatrelativehumidity

        temp = setpoint_temp if SETPOINTS else room_temp
        humidity = setpoint_humidity if SETPOINTS else room_humidity

        self.temp_char.set_value(temp)
        self.humid_char.set_value(humidity)

    def stop(self):
        print('Stopping accessory.')

def get_accessory(driver):
    return TemperatureSensor(driver, ACC_NAME)

driver = AccessoryDriver(port=USE_PORT)
driver.add_accessory(accessory=get_accessory(driver))
signal.signal(signal.SIGTERM, driver.signal_handler)
driver.start()