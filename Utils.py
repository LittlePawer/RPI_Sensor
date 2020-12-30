import argparse
import logging
import os,sys, datetime, time

def SetupLogger(Debug = False):
    if Debug:
        logging.basicConfig(
            level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(
            level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    return logging

def GetConfig(ConfigFile):
    import configparser
    config = configparser.ConfigParser()
    config.optionxform=str
    config.read(ConfigFile)

    return config

def ReadSensor(Sensor, Pin):
    logger = SetupLogger().getLogger(__name__)

    if 'DHT' in Sensor:
        # using Adafruit_DHT module to read the sensor
        try:
            import Adafruit_DHT
        except :
            logger.error('Adafruit_DHT module is not installed correctly! Try pip3 install Adafruit_DHT? Abort now!')
            sys.exit()

        DHT_Sensor_Map = {"DHT11": Adafruit_DHT.DHT11, "DHT22": Adafruit_DHT.DHT22}

        sensor = DHT_Sensor_Map[Sensor]

        humidity, temperature = Adafruit_DHT.read_retry(sensor, Pin)
        
        if humidity is None or temperature is None :
            logger.error('Can not read data from {0} in PIN {1}! Abort!'.format(Sensor, Pin))
            sys.exit()
        
        return humidity, temperature

    elif 'SHT3X' in Sensor:
        # using adafruit_sht31d module to read the data
        try:
            import board, busio, adafruit_sht31d
        except:
            logger.error('board, busio, adafruit_sht31d modules were not properly installed! Abort!')
            sys.exit()

        i2c = busio.I2C(board.SCL, board.SDA)
        I2C_sensor = adafruit_sht31d.SHT31D(i2c)
        humidity = I2C_sensor.relative_humidity
        temperature = I2C_sensor.temperature

        if humidity is None or temperature is None :
            logger.error('Can not read data from {0} in PIN {1}! Abort!'.format(Sensor, Pin))
            sys.exit()
        
        logger.info('Turn on the heater for 1 second')
        I2C_sensor.heater = True
        time.sleep(1)
        I2C_sensor.heater = False

        return humidity, temperature

    else:
        logger.error('Not a supported sensor type! Abort!')
        sys.exit()


def SetupDB(DBConfig_Dict):
    logger = SetupLogger().getLogger(__name__)

    host = DBConfig_Dict['host']
    responce = os.system("ping -c 1 {0}".format(host))
    if responce != 0:
        logger.error("The host: {0} is not respnding! Abort!".format(host))
    
    # check if the influxd is running in host server
    logger.info('Checking the setups of influxDB:')
    try:
        import paramiko
    except :
        logger.error('Can not find paramiko to check the setups in host server! Abort!')
        sys.exit()
    
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys() # you must establish the trust with the server using ssh first. Otherwise, the ssh connection can't be setup!
    try:
        ssh.connect(host, username=DBConfig_Dict['hostname'], password=DBConfig_Dict['hostpassword'])
    except:
        logger.error("ssh connection to server {0} can not be establish! Abort!".format(host))
        sys.exit()

    # checking if the influxDB is running on the server
    cmd = "ps -a"
    output_lines = ExcuteRemoteCMD(ssh, cmd)
    if "influxd" not in str(output_lines):
        logger.error("influxd is not running on the host: {0}! Abort!".format(host))
        sys.exit()
    else:
        logger.info("influxd is running well in server!")

    # checking the user informations for the DataBase
    user = DBConfig_Dict['user']
    cmd = "influx user list"
    output_lines = ExcuteRemoteCMD(ssh, cmd)
    if user not in str(output_lines):
        logger.warning('user: {0} is not existing in influxDB in the host: {1}! Will create the user for you!'.format(user, host))

        cmd = "influx user create -n {0} -p 12345678".format(user)
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        if "ERROR" not in str(output_lines):
            logger.info("user: {0} is created succesfully! With initial password: 12345678. Please change this manually!".format(user))
        else:
            logger.error("Something wrong when creating DataBase user for you! Abort!")
            sys.exit()
        
        logger.info("Start auth for the user now!")
        cmd = "influx auth create -u {0} --read-buckets --read-checks --read-dashboards --read-dbrps --read-notificationEndpoints --read-notificationRules --read-orgs --read-tasks   --read-telegrafs --read-user  --write-buckets  --write-checks --write-dashboards  --write-dbrps  --write-notificationEndpoints --write-notificationRules --write-orgs --write-tasks --write-telegrafs --write-user".format(user)
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        if "ERROR" not in str(output_lines):
            logger.info("auth for user: {0} is created succesfully!".format(user))
        else:
            logger.error("Something wrong when creating DataBase auth for user {0}! Abort!".format(user))
            sys.exit()

    # checking the org informations for the DataBase
    org = DBConfig_Dict['org']
    cmd = "influx org list"
    output_lines = ExcuteRemoteCMD(ssh, cmd)
    if org not in str(output_lines):
        logger.warning('org: {0} is not existing in influxDB in the host: {1}! Will create the user for you!'.format(org, host))

        cmd = "influx org create -n {0}".format(org)
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        if "ERROR" not in str(output_lines):
            logger.info("org: {0} is created succesfully!".format(org))
        else:
            logger.error("Something wrong when creating DataBase org {0}! Abort!".format(org))
            sys.exit()


    # checking the bucket informations for the DataBase
    bucket = DBConfig_Dict['bucket']
    cmd = "influx bucket list"
    output_lines = ExcuteRemoteCMD(ssh, cmd)
    if bucket not in str(output_lines):
        logger.warning('bucket: {0} is not existing in influxDB in the host: {1}! Will create the user for you!'.format(bucket, host))

        cmd = "influx bucket create -n {0} -r 0".format(bucket)
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        if "ERROR" not in str(output_lines):
            logger.info("bucket: {0} is created succesfully!".format(bucket))
        else:
            logger.error("Something wrong when creating DataBase bucket {0}! Abort!".format(bucket))
            sys.exit()


    # checking the token informations for the DataBase:
    token = DBConfig_Dict['token']
    if token == "":
        logger.info("Obtain token according to user")
        cmd = "influx auth list"
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        for line in output_lines:
            if user not in str(line): continue
            token = line[str(line).find("\\t\\t\\t\\t")+8 : str(line).find("==\t")+2]
    else:
        cmd = "influx auth list"
        output_lines = ExcuteRemoteCMD(ssh, cmd)
        GotToken = False
        for line in output_lines:
            if user in str(line) and token in str(line):
                GotToken = True
        if not GotToken:
            logger.error("Not a correct token: {0}! Abort!".format(token))
            sys.exit()
    
    logger.info("influxDB hostname: {0}".format(DBConfig_Dict["hostname"]))
    logger.info("influxDB host: {0}".format(DBConfig_Dict["host"]))
    logger.info("influxDB user: {0}".format(user))
    logger.info("influxDB org: {0}".format(org))
    logger.info("influxDB token: {0}".format(token))
    logger.info("influxDB bucket: {0}".format(bucket))

    url = "http://{0}:8086".format(host)

    DB_Dict = {"token": token, "org": org, "bucket": bucket, "url": url, "measurement": DBConfig_Dict["measurement"], "tag": DBConfig_Dict["tag"], "field": DBConfig_Dict["field"]}

    return DB_Dict

def ExcuteRemoteCMD(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdin.close()
    stderr.close()
    output_lines = stdout.read().splitlines()
    return output_lines


def ReAnWr_Data(DB_info, Sensor_info, start, end, step):
    logger = SetupLogger().getLogger(__name__)

    try:
        from influxdb_client import InfluxDBClient, Point, WritePrecision
        from influxdb_client.client.write_api import SYNCHRONOUS
    except :
        logger.error("influxdb_client module was not installed! Abort!")
        sys.exit()

    if start == "0" and end == "0":
        logger.info("Read and Write data on and on!")
        while True:
            humidity, temperature = ReadSensor(Sensor_info['sensor'],Sensor_info['pin'])
            
            point = Point(DB_info['measurement']).field("temperature", float
            (temperature)).field("humidity", float(humidity)).time(datetime.datetime.utcnow(), WritePrecision.NS)
            logger.info('Time={2}  Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity, datetime.datetime.now()))

            DB_info['write_api'].write(DB_info['bucket'], DB_info['org'], point)
            
            time.sleep(int(step))

    else:
        logger.error("Not a supported start and end time yet! Abort!")
        sys.exit()
