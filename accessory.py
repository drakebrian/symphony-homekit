import logging
import os
import pyhap.loader as loader
import signal
import yaml
from pyhap.accessory import Accessory
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_SENSOR
from waterfurnace.waterfurnace import WaterFurnace

CONFIG_FILE = 'config.yml'
with open(CONFIG_FILE) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

user = os.environ.get('SYMPHONY_USER')
pwd = os.environ.get('SYMPHONY_PWD')

if not user or not pwd:
    logging.error('Username or password variables not set')
    exit(1)

try:
    wf = WaterFurnace(user, pwd)
    login = wf.login()
except Exception as ex:
    logging.error('Symphony login failed. Check username and password')
    exit(1)

class TemperatureSensor(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        temp_service = self.add_preload_service('TemperatureSensor')
        self.temp_char = temp_service.get_characteristic('CurrentTemperature')

        temp_humidity = self.add_preload_service('HumiditySensor')
        self.humid_char = temp_humidity.get_characteristic('CurrentRelativeHumidity')

    @Accessory.run_at_interval(config['accessory']['polling_interval'])
    def run(self):
        data = wf.read()

        setpoint_temp = float(data.tstatactivesetpoint) if config['accessory']['functions']['temperature']['celsius'] else (float(data.tstatactivesetpoint)-32) * 5/9
        room_temp = float(data.tstatroomtemp) if config['accessory']['functions']['temperature']['celsius'] else (float(data.tstatroomtemp)-32) * 5/9
        temp = setpoint_temp if config['accessory']['functions']['temperature']['setpoint'] else room_temp
        self.temp_char.set_value(temp)

        setpoint_humidity = data.tstathumidsetpoint
        room_humidity = data.tstatrelativehumidity
        humidity = setpoint_humidity if config['accessory']['functions']['humidity']['setpoint'] else room_humidity
        self.humid_char.set_value(humidity)

    def stop(self):
        logging.info('Stopping accessory')

def get_accessory(driver):
    return TemperatureSensor(driver, config['accessory']['name'])

driver = AccessoryDriver(port=config['accessory']['port'])
driver.add_accessory(accessory=get_accessory(driver))
signal.signal(signal.SIGTERM, driver.signal_handler)
driver.start()