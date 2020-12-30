# Quick start:
Run the following line in the raspberry PI machine with sensor correct connected:
```python
python3 ReadData.py --ConfigFile <PATH TO CONFIGFILE>
```
Then you could find the data in `http://<host>:8086`
- `ReadData.py` will find the `configfile.ini` and do the rest of things according to your configurations documented in `configfile.ini`

## `config.ini`:
It is the file for all the configurations. It has serval sections:
### sensor:
```ini
[sensor]
type = DHT11
pin = 9
```
- In this section, one should correctly set the sensor type and the PIN for the connection if necessary:
    - In this example, the sensor we will read is DHT11 and connected to RPI with 9th pin
    - one can keep `pin` empty if there is no need e.g: sensors with I2C protocol 

### database:
```ini
[database]
hostname = atlasitk
host = 10.147.20.184
hostpassword = ATLASITK
user = test
token = 
org = IHEP
bucket = test_b
measurement = test_DHT11
tag = 
filed =
```
- In this section one should provide the server's information to host the influxDB service and the information to setup the influxDB in the server
- `SetupDB` function in `Utils.py` will check the availability of the host first and also check if the `influxd` service is running on the server
- Then `SetupDB` function will also setup the `user`, `org`, `bucket` for you according to your configuration

### DAQ:
```ini
[DAQ]
type = scan
start =  0
end = 0
step = 10
```
- In this section one should setup the type of the DAQ you want.
- `Scan` means read the sensor time to time with period setting by `step`
- `Period` means read the sensor from `start` to `end` with time period set by `step`

# To Dos:
1. `sync` is not developed yet which will be used to synchronize data from RPI to some other PC for backups
2. Many other functions could be added according to the needs

# Note:
1. If one want to access the data universally, one could use ZeroTier to set all devices into one "cloud net"