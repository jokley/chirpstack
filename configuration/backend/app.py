from flask import Flask, json, render_template, request,jsonify
from datetime import datetime
from flask_cors import CORS
from flask_mqtt import Mqtt
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import sys



#TIMESTAMP_NOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).isoformat()
#TIMESTAMP_NOW_OFFSET = pytz.timezone("Europe/Berlin").utcoffset(datetime.now()).total_seconds()
#TIMESTAMP_NOW_EPOCHE = int(datetime.now().timestamp()+TIMESTAMP_NOW_OFFSET)  

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


app = Flask(__name__)
CORS(app)

with app.app_context():
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Europe/Berlin'})
    scheduler.add_job(venti_control, 'interval', minutes=1, args=['87','1'], replace_existing=True, id='venti_control')
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


@app.route('/venti',methods = ['POST', 'GET'])
def switch():
    if request.method == 'POST':
        data = request.get_json()
        CMD = data['cmd']
        TM = data['tm']
        STOCK = data['stock']

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
  
