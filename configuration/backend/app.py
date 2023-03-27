from flask import Flask, json, render_template, request,jsonify
from datetime import datetime, timedelta,timezone
from flask_cors import CORS
from flask_mqtt import Mqtt
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, Dialect
from influxdb_client.client.write_api import SYNCHRONOUS
import logging



load_dotenv()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
      
    ]
)

def get_influxdb_client():
    URL = "http://172.16.238.16:8086"
    TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)

    return client


def get_timestamp_now():
    TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
    return TIMESTAMP_NOW

def get_timestamp_now_offset():
    TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
    return TIMESTAMP_NOW_OFFSET

def get_timestamp_now_epoche():
    TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+get_timestamp_now_offset())
    return TIMESTAMP_NOW_EPOCHE 

def venti_cmd(cmd):
    if cmd == 'on':
        mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwEA\" }")
    elif cmd == 'off':
        mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwAA\" }")



def venti_control():
    data = get_min_max_values()
    humMin = data[0]['humidityMin']
    humMax = data[0]['humidityMax']
    sDefMin = data[0]['sDefMin']
    sDefMax = data[0]['sDefMax']
    tempMin = data[0]['temperatureMin']
    tempMax = data[0]['temperatureMax']
    tsMin = data[0]['trockenMasseMin']
    tsMax = data[0]['trockenMasseMax']

    dataOut = get_outdoor_values()
    humOut = dataOut[0]['humidityOut']
    sDefOut = dataOut[0]['sDefOut']
    tempOut = dataOut[0]['temperatureOut']
    tsOut = dataOut[0]['trockenMasseOut']


    dataVenti = get_venti_control_values()
    startTime = dataVenti[0]['mode'][0]
    mode = dataVenti[0]['mode'][1]
    tsSoll =dataVenti[0]['trockenMasseSoll'][1]
    stock = int(dataVenti[0]['stockaufbau'][1])
    stock *= 3600

    dataLastTime = get_venti_lastTimeOn()
    lastOn = dataLastTime[0]['lastTimeOn']
    
    DST =  get_timestamp_now_offset()
    timeNow = get_timestamp_now_epoche()

    startTimeStock = (startTime + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    lastTimeOn = (lastOn + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    remainingTimeStock =     int(timeNow - startTimeStock)
    remainingTimeInterval =  int(timeNow - lastTimeOn)

    # Überhitzungsschutz
    if tempMax >= 35:
        venti_cmd('on')
        app.logger.info(mode)
        app.logger.info('Überhitzungsschutz')
        app.logger.info('Temperatur: {}'.format(tempMax))
       
    # Stockaufbau
    elif mode == 'auto' and remainingTimeStock <= stock:
        venti_cmd('on')
        app.logger.info(mode)
        app.logger.info('Stockaufbau:')
        app.logger.info('Restzeit: {}'.format(remainingTimeStock/3600))
    # Trockenmasse Automatik
    elif mode == 'auto' and sDefOut >= sDefMin+2 and tsMin <= tsSoll:
        venti_cmd('on')
        app.logger.info(mode)
        app.logger.info('Trockenmasse Automatik:')
        app.logger.info('SDef diff: {}'.format(sDefOut-sDefMin))
        app.logger.info('TS ist: {}'.format(tsMin))
   
    # Intervall Belüftung
    elif mode == 'auto' and humMax > 95 and remainingTimeInterval >= 86400:
        venti_cmd('on')
        app.logger.info(mode)
        app.logger.info('Intervall Belüftung')
        app.logger.info('Restzeit: {}'.format(remainingTimeInterval/3600))
      
    else:
    # Belüftung aus
        venti_cmd('off')
        app.logger.info(mode)
        app.logger.info('Blefüftung aus')
              
   # sys.stdout.flush()


def venti_auto(cmd, trockenMasse,stockAufbau):
    
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")

    client = get_influxdb_client()

    write_api = client.write_api(write_options=SYNCHRONOUS)

    record = [
	Point("venti").field("mode", cmd).field("trockenmasse", trockenMasse).field("stockaufbau", stockAufbau),
    ]      

    write_api.write(bucket="jokley_bucket", org=ORG, record=record)
    client.close()

def get_venti_lastTimeOn():
    client = get_influxdb_client()

    query = '''from(bucket: "jokley_bucket")
                |> range(start: -2d)
                |> filter(fn: (r) => r["device_name"] == "fan")
                |> filter(fn: (r) => r["_measurement"] == "device_frmpayload_data_RO1_status")
                |> filter(fn: (r) => r["_value"] == "ON")
                |> last()
            '''

    result = client.query_api().query(query=query)

    results = []
    for table in result:
        for record in table.records:
            results.append((record.get_time()))
    
    results2 = []
    names = ['lastTimeOn']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)
def get_venti_control_values():
    client = get_influxdb_client()

    query = ''' from(bucket: "jokley_bucket")
                    |> range(start: -30d)
                    |> filter(fn: (r) => r["_measurement"] == "venti")
		            |> last()
                '''

    result = client.query_api().query(query=query)

    results = []
    for table in result:
        for record in table.records:
            results.append((record.get_time(), record.get_value()))
    
    results2 = []
    names = ['mode','stockaufbau','trockenMasseSoll']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)
    

def get_outdoor_values():
    client = get_influxdb_client()

    query = '''from(bucket: "jokley_bucket")
                |> range(start: -1h)
                |> filter(fn: (r) => r["device_name"] == "outdoor")
                |> filter(fn: (r) => r["_measurement"] == "device_frmpayload_data_TempC_SHT" or r["_measurement"] == "device_frmpayload_data_Hum_SHT" or r["_measurement"] == "device_frmpayload_data_TS_SHT" or r["_measurement"] == "device_frmpayload_data_SDef_SHT")
                |> last()
            '''
    result = client.query_api().query(query=query)
   
    results = []
    for table in result:
        for record in table.records:
            results.append(( record.get_value()))
    
    results2 = []
    names = ['humidityOut','sDefOut','trockenMasseOut','temperatureOut']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)

def get_min_max_values():
    client = get_influxdb_client()

    # query = '''data = from(bucket: "jokley_bucket")
    #             |> range(start: -1h)
    #             |> filter(fn: (r) => r["device_name"] == "probe01" or r["device_name"] == "probe02")
    #             |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" or r["_measurement"] == "device_frmpayload_data_sdef" )
    #             |> last()
    #             |> group(columns: ["_measurement"])
    #             |> sort(columns: ["_measurement"])
 
    #         data_min = data
    #             |> min()
    #             |> set(key:"_measurement", value:"min")
    #             |> sort(columns: ["_measurement"])
    #             |> yield(name: "min") 

    #         data_max = data
    #             |> max()
    #             |> set(key:"_measurement", value:"max")
    #             |> sort(columns: ["_measurement"])
    #             |> yield(name: "max") 

    #         '''

    query = '''
            tmin = from(bucket: "jokley_bucket")
                |> range(start: -10m)
                |> filter(fn: (r) => r["device_name"] == "probe01" or r["device_name"] == "probe02")
                |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" or r["_measurement"] == "device_frmpayload_data_sdef" )
                |> last()
                |> group(columns: ["_measurement"])
                |> min()

            tmax = from(bucket: "jokley_bucket")
                |> range(start: -10m)
                |> filter(fn: (r) => r["device_name"] == "probe01" or r["device_name"] == "probe02")
                |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" or r["_measurement"] == "device_frmpayload_data_sdef" )
                |> last()
                |> group(columns: ["_measurement"])
                |> max()

            union(tables: [tmin, tmax])
                |> sort(columns: ["_measurement", "_value"])
    
            '''

    result = client.query_api().query(query=query)
   
    results = []
    for table in result:
        for record in table.records:
            results.append((  record.get_value()))
    
    results2 = []
    #names = ['humidityMin','sDefMin','temperatureMin','trockenMasseMin','humidityMax','sDefMax','temperatureMax','trockenMasseMax']
    names = ['humidityMin','humidityMax','sDefMin','sDefMax','temperatureMin','temperatureMax','trockenMasseMin','trockenMasseMax']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)


app = Flask(__name__)
CORS(app)


with app.app_context():
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Europe/Berlin'})
    scheduler.add_job(venti_control, 'interval', minutes=1,  replace_existing=True, id='venti_control')
    scheduler.start()


app.config['MQTT_BROKER_URL'] = "172.16.238.15"
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] =20


app.secret_key = 'hi'
mqtt = Mqtt(app)
    
# @mqtt.on_connect()




@app.route('/')
def home():
    return jsonify('Welcome to venti')

@app.route('/logging')
def default_route():
    """Default route"""
    app.logger.debug('this is a DEBUG message')
    app.logger.info('this is an INFO message')
    app.logger.warning('this is a WARNING message')
    app.logger.error('this is an ERROR message')
    app.logger.critical('this is a CRITICAL message')
    return jsonify('hello world')

@app.route('/time')
def time():
    return jsonify(get_timestamp_now_epoche(),get_timestamp_now(),get_timestamp_now_offset())

@app.route('/influx')
def influx():

    data = get_min_max_values()
    humMin = data[0]['humidityMin']
    humMax = data[0]['humidityMax']
    sDefMin = data[0]['sDefMin']
    sDefMax = data[0]['sDefMax']
    tempMin = data[0]['temperatureMin']
    tempMax = data[0]['temperatureMax']
    tsMin = data[0]['trockenMasseMin']
    tsMax = data[0]['trockenMasseMax']

    dataOut = get_outdoor_values()
    humOut = dataOut[0]['humidityOut']
    sDefOut = dataOut[0]['sDefOut']
    tempOut = dataOut[0]['temperatureOut']
    tsOut = dataOut[0]['trockenMasseOut']


    dataVenti = get_venti_control_values()
    startTime = dataVenti[0]['mode'][0]
    mode = dataVenti[0]['mode'][1]
    tsSoll =dataVenti[0]['trockenMasseSoll'][1]
    stock = int(dataVenti[0]['stockaufbau'][1])
    stock *= 3600

    dataLastTime = get_venti_lastTimeOn()
    lastOn = dataLastTime[0]['lastTimeOn']
    
    DST =  get_timestamp_now_offset()
    timeNow = get_timestamp_now_epoche()

    startTimeStock = (startTime + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    lastTimeOn = (lastOn + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    remainingTimeStock =     int(timeNow - startTimeStock)
    remainingTimeInterval =  int(timeNow - lastTimeOn)

   


    return jsonify('{},{},{}'.format(sDefMin,sDefMax,sDefOut))
    #return jsonify(dataVenti[0]['mode'][0])
    #return jsonify('{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(humMin, humMax,tempMin,tempMax,tsMin,tsMax,humOut,tempOut,tsOut,startTimeStock,mode,tsSoll,stock))

@app.route('/venti',methods = ['POST', 'GET'])
def switch():
    if request.method == 'POST':
        data = request.get_json()
        CMD = data['cmd']
        TM = data['tm']
        try:
            STOCK = data['stock']
        except KeyError:
             STOCK = '0'
    
        if CMD == 'on':
            venti_cmd(CMD)
            venti_auto(CMD,TM,'0')
            return jsonify('Venti on')
        elif CMD == 'off':
            venti_cmd(CMD)
            venti_auto(CMD,TM,'0')
            return jsonify('Venti off')
        elif CMD == 'auto':
            venti_auto(CMD,TM,STOCK)
            return jsonify('Venti auto')
        else:
            return jsonify('No command send!')
            
    if request.method == 'GET':
        CMD = request.args.get('cmd', default = 'auto', type = str)

        if CMD == 'on':
            venti_cmd(CMD)
            return jsonify('Venti on')
        elif CMD == 'off':
            venti_cmd(CMD)
            return jsonify('Venti off')
        else:
            return jsonify('No command send!')



    
    
#if __name__ == "__main__":
    #app.run(host="0.0.0.0",port=5001, debug=True)
