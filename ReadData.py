import argparse
import logging
import os,sys,copy
import Utils

parser = argparse.ArgumentParser()
parser.add_argument('--ConfigFile' , type=str, default='./config.ini', help='config file for everything! Should be .ini file!')
parser.add_argument('--Debug', type=bool, default=False, help='options for debug mode')
options = parser.parse_args()


logger = Utils.SetupLogger(options.Debug).getLogger(__name__)

logger.info('>>> ... Get input options ... <<<')
for setting in dir(options):
    if not setting[0] == "_":
        logger.info("Setting: {: >20} {: >40}".format(setting, eval("options.%s" % setting)))

# Read config file first!
if not os.path.exists(options.ConfigFile):
    logger.error('Not a correct config file! Abort!')
    sys.exit()

config = Utils.GetConfig(options.ConfigFile)
logger.info('Using config file from {0}'.format(options.ConfigFile))

# Setup influxDB configuration
logger.info('Start to setup influxDB')
DB_Dict = Utils.SetupDB(config['database'])

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except :
    logger.error("influxdb_client module was not installed! Abort!")
    sys.exit()

DB_client = InfluxDBClient(url=DB_Dict['url'], token=DB_Dict["token"])
write_api = DB_client.write_api(write_options=SYNCHRONOUS)

DB_info = copy.deepcopy(DB_Dict)
DB_info["write_api"] = write_api

# See the type of the sensors
SupportedSensorList = ['DHT11','DHT22','SHT3X']
Sensor = config['sensor']['type']
Pin = config['sensor']['pin']
if Sensor not in SupportedSensorList:
    logger.error('Not a supported Sensor! Abort!')
    sys.exit()
logger.info('Using sensor {0} in Pin {1}'.format(Sensor, Pin))
Sensor_info = {"sensor": Sensor, "pin": Pin}

# check the requirement on the DAQ side:
# type = "scan"/"period"
# if type = "scan" there is no need for start and end

DAQ_type = config['DAQ']['type']
if DAQ_type == "period":
    logger.error("Periodly checking is not available for now! Abort!")
    sys.exit()
elif DAQ_type == "scan":
    logger.info("Will start scanning for the reads of the sensors")
    start = "0"
    end = "0"
    step = config["DAQ"]["step"]
    try:
        Utils.ReAnWr_Data(DB_info, Sensor_info, start, end, step)
    except:
        logger.error("Something wrong when read and write sensor data to DB! Abort!")
        sys.exit()
else:
    logger.error("DAQ type: {0} is not available for now! Abort!".format(DAQ_type))
    sys.exit()

