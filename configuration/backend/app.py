from flask import Flask, json, render_template, request,jsonify
from datetime import datetime
from flask_cors import CORS
from flask_mqtt import Mqtt
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, Dialect
from influxdb_client.client.write_api import SYNCHRONOUS



load_dotenv()

def get_influxdb_client():
    URL = "http://172.16.238.16:8086"
    TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    #client = InfluxDBClient(url="http://172.16.238.16:8086", token="Jr5krSrSA6UlKD7vQifU8XJ1U9UZzpKYCNx7vs6kizYc3Bp51XYNlrpsoJXYRdLh2w_c7XNnFgplvnr0ebouDQ==", org="jokley")

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

def venti_control(trockenMasse,stockAufbau):
    print('Auto on')
    print(trockenMasse)
    print(stockAufbau)
    sys.stdout.flush()
    

def get_min_max_values():
    client = get_influxdb_client()

    query = '''data = from(bucket: "jokley_bucket")
                |> range(start: -10m)
                |> filter(fn: (r) => r["device_name"] == "probe01" or r["device_name"] == "probe02")
                |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" )
                |> last()
                |> group(columns: ["_measurement"])
                |> sort(columns: ["_measurement"])
 
            data_min = data
                |> min()
                |> set(key:"_measurement", value:"min")
                |> sort(columns: ["_measurement"])
                |> yield(name: "min") 

            data_max = data
                |> max()
                |> set(key:"_measurement", value:"max")
                |> sort(columns: ["_measurement"])
                |> yield(name: "max") 

            '''

    result = client.query_api().query(query=query)
   
    results = []
    for table in result:
        for record in table.records:
            results.append((  record.get_value()))
    
    results2 = []
    names = ['humidityMin','temperatureMin','trockenMasseMin','humidityMax','temperatureMax','trockenMasseMax']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)





app = Flask(__name__)
CORS(app)


with app.app_context():
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Europe/Berlin'})
    scheduler.add_job(venti_control, 'interval', minutes=5, args=['87','1'], replace_existing=True, id='venti_control')
    scheduler.start()


app.config['MQTT_BROKER_URL'] = "172.16.238.15"
# app.config['MQTT_BROKER_URL'] = "10.1.10.235"
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] =20


app.secret_key = 'hi'
mqtt = Mqtt(app)
    
# @mqtt.on_connect()




@app.route('/')
def home():
    return jsonify('Welcome to venti')

@app.route('/time')
def time():
    return jsonify(get_timestamp_now_epoche(),get_timestamp_now(),get_timestamp_now_offset())

@app.route('/influx')
def influx():

    data = get_min_max_values()
    tempMin = data('temperatureMin')

    return jsonify(tempMin)

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
            mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwEA\" }")
            return jsonify('Venti on')
        elif CMD == 'off':
            mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwAA\" }")
            return jsonify('Venti off')
        elif CMD == 'auto':
            scheduler.modify_job('venti_control',  args=[TM,STOCK])
            return jsonify('Venti auto')
        else:
            return jsonify('No command send!')
            
    if request.method == 'GET':
        CMD = request.args.get('cmd', default = 'auto', type = str)

        if CMD == 'on':
            mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwEA\" }")
            return jsonify('Venti on')
        elif CMD == 'off':
            mqtt.publish("application/9b558903-28f2-4508-b219-7ddd180dbc90/device/a840418c51868361/command/down" , "{\"devEui\":\"a840418c51868361\", \"confirmed\": true, \"fPort\": 10, \"data\": \"AwAA\" }")
            return jsonify('Venti off')
        else:
            return jsonify('No command send!')



    
    
#if __name__ == "__main__":
    #app.run(host="0.0.0.0",port=5001, debug=True)
  
