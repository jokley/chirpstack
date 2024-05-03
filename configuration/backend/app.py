from flask import Flask, json, render_template, request,jsonify,send_file
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

rfh = logging.handlers.RotatingFileHandler(
    filename='debug.log', 
    mode='a',
    maxBytes=1000,
    backupCount=0,
    encoding=None,
    delay=0
)

logging.Formatter.converter = lambda *args: datetime.now(pytz.timezone("Europe/Berlin")).timetuple()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        rfh
        #logging.FileHandler("debug.log"), 
    ]
)

#logging.getLogger('apscheduler').setLevel(logging.DEBUG)


def get_influxdb_client():
    URL = "http://172.16.238.16:8086"
    TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)

    return client

def get_time_now():
    TIMENOW = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).strftime("%H:%M")
    return TIMENOW

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
    lastOff = dataLastTime[0]['lastTimeOff']
    
    DST =  get_timestamp_now_offset()
    timeNow = get_timestamp_now_epoche()
    timeNowIso = get_time_now()

    startTimeStock = (startTime + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    lastTimeOn = (lastOn + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    lastTimeOff = (lastOff + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    remainingTimeStock =     int(timeNow - startTimeStock)
    remainingTimeInterval =  int(timeNow - lastTimeOn)
    lastTimeDiffOff =  int(timeNow - lastTimeOff)
    lastTimeDiffOn =  int(timeNow - lastTimeOn)

    pramsVenti = get_venti_control_param_values()
    #startTime = pramsVenti[0]['sdef_on'][0]
    sdef_on = pramsVenti[0]['sdef_on'][1]/10
    sdef_hys = pramsVenti[0]['sdef_hys'][1]/10
    uschutz_on = pramsVenti[0]['uschutz_on'][1]/10
    uschutz_hys = pramsVenti[0]['uschutz_hys'][1]/10
    intervall_on =  pramsVenti[0]['intervall_on'][1]/10
    intervall_time =  (pramsVenti[0]['intervall_time'][1]/10)*3600
    intervall_enable = pramsVenti[0]['intervall_enable'][1]

    # Überhitzungsschutz
    if tempMax >= uschutz_on:
        venti_cmd('on')
        app.logger.info('****************************************')
        app.logger.info('Mode: {}'.format(mode))
        app.logger.info('Überhitzungsschutz aktiv!')
        app.logger.info('Temperatur: {}'.format(tempMax))

    # Temp Ok und Automatik
    elif tempMax+uschutz_hys < uschutz_on and mode == 'auto':
       
        # Stockaufbau
        if  remainingTimeStock <= stock and stock > 0:
            venti_cmd('on')
            app.logger.info('****************************************')
            app.logger.info('Mode: {}'.format(mode))
            app.logger.info('Stockaufbau')
            app.logger.info('Restzeit: {}'.format(stock-remainingTimeStock))

        # Trockenmasse Automatik
        elif sDefOut >= sDefMin+sdef_hys and sDefOut >= sdef_on and tsMin <= tsSoll:
            venti_cmd('on')
            app.logger.info('****************************************')
            app.logger.info('Mode: {}'.format(mode))
            app.logger.info('Lüfter ein')
            app.logger.info('SDef min: {} | SDef out: {}'.format(sDefMin,sDefOut))
            app.logger.info('SDef diff: {}'.format(sDefOut-sDefMin))
            app.logger.info('TS ist: {} | TS soll: {}'.format(tsMin,tsSoll))
            app.logger.info('TS diff: {}'.format(tsSoll-tsMin))
            app.logger.info('Dauer aus: {}'.format(remainingTimeInterval))
    
        # Intervall Belüftung rel. 95%  und 12h last on und Interval von 12min und zwischen 08:00 und 22:00 // and (timeNowIso >= '08:00' and timeNowIso <= '22:00')
        elif humMax > intervall_on and (lastTimeDiffOff >= intervall_time or lastTimeDiffOff <= 720):
                venti_cmd('on')
                app.logger.info('****************************************')
                app.logger.info('Mode: {}'.format(mode))
                app.logger.info('Intervall Belüftung')
                app.logger.info('Interall lastTimeOn: {}'.format(lastOn))
                app.logger.info('Interall lastTimeOff: {}'.format(lastOff))
                app.logger.info('Interall Schwelle: {}'.format(intervall_on))
                app.logger.info('Intervall: {}'.format(intervall_time))
                app.logger.info('Restzeit: {}'.format(720-remainingTimeInterval))
        
        elif remainingTimeStock > stock and (sDefOut < sDefMin+sdef_hys-1 or tsMin > tsSoll or sDefOut+0.5 < sdef_on):
        # Belüftung aus
            venti_cmd('off')
            app.logger.info('****************************************')
            app.logger.info('Mode: {}'.format(mode))
            app.logger.info('Lüfter aus')
            app.logger.info('SDef min: {} | SDef out: {}'.format(sDefMin,sDefOut))
            app.logger.info('SDef diff: {}'.format(sDefOut-sDefMin))
            app.logger.info('TS ist: {} | TS soll: {}'.format(tsMin,tsSoll))
            app.logger.info('TS diff: {}'.format(tsSoll-tsMin))
            app.logger.info('Dauer aus: {}'.format(remainingTimeInterval))

            if remainingTimeInterval >= 7200 and tsSoll-tsMin <= 0.5:
            # Automaitk aus
                venti_auto('off',tsSoll,'0')
                app.logger.info('****************************************')
                app.logger.info('Automatik aus')
                app.logger.info('TS ist: {} | TS soll: {}'.format(tsMin,tsSoll))

        else:
         # Automaik ein nur Loggoger Info
            app.logger.info('****************************************')
            app.logger.info('Mode: {}'.format(mode))
            app.logger.info('Lüfter aus')
            app.logger.info('SDef min: {} | SDef out: {}'.format(sDefMin,sDefOut))
            app.logger.info('SDef diff: {}'.format(sDefOut-sDefMin))
            app.logger.info('TS ist: {} | TS soll: {}'.format(tsMin,tsSoll))
            app.logger.info('TS diff: {}'.format(tsSoll-tsMin))
            app.logger.info('Dauer aus: {}'.format(remainingTimeInterval))

    
    elif tempMax+uschutz_hys < uschutz_on and mode == 'off':
        venti_cmd('off')

   



def venti_auto(cmd, trockenMasse,stockAufbau):
    
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")

    client = get_influxdb_client()

    write_api = client.write_api(write_options=SYNCHRONOUS)

    record = [
	Point("venti").field("mode", cmd).field("trockenmasse", trockenMasse).field("stockaufbau", stockAufbau),
    ]      

    write_api.write(bucket="jokley_bucket", org=ORG, record=record)
    client.close()

def venti_auto_param(sdef_on, sdef_hys,uschutz_on,uschutz_hys,intervall_on,intervall_time,intervall_enable):
    
    ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")

    sdef_on = int(sdef_on*10)
    sdef_hys = int(sdef_hys*10)
    uschutz_on = int(uschutz_on*10)
    uschutz_hys = int(uschutz_hys*10)
    intervall_on = int(intervall_on*10)
    intervall_time = int(intervall_time*10)
    intervall_enable = intervall_enable


    client = get_influxdb_client()

    write_api = client.write_api(write_options=SYNCHRONOUS)

    record = [
	Point("venti_param").field("sdef_on", sdef_on).field("sdef_hys", sdef_hys).field("uschutz_on", uschutz_on).field("uschutz_hys", uschutz_hys).field("intervall_on", intervall_on).field("intervall_time", intervall_time).field("intervall_enable", intervall_enable),
    ]      

    write_api.write(bucket="jokley_bucket", org=ORG, record=record)
    client.close()

def get_venti_lastTimeOn():
    client = get_influxdb_client()

    query = '''on = from(bucket: "jokley_bucket")
                        |> range(start: -2d)
                        |> filter(fn: (r) => r["device_name"] == "fan")
                        |> filter(fn: (r) => r["_measurement"] == "device_frmpayload_data_RO1_status")
                        |> filter(fn: (r) => r["_value"] == "ON")
                        |> last()

                off = from(bucket: "jokley_bucket")
                        |> range(start: -2d)
                        |> filter(fn: (r) => r["device_name"] == "fan")
                        |> filter(fn: (r) => r["_measurement"] == "device_frmpayload_data_RO1_status")
                        |> filter(fn: (r) => r["_value"] == "OFF")
                        |> last()

                union(tables: [on, off])
                |> sort(columns: ["_measurement", "_value"])
            '''
    
    result = client.query_api().query(query=query)
   
    results = []
    for table in result:
        for record in table.records:
            results.append((  record.get_time()))
    
    results2 = []
    names = ['lastTimeOff','lastTimeOn']
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

def get_venti_control_param_values():
    client = get_influxdb_client()

    query = ''' from(bucket: "jokley_bucket")
                    |> range(start: -30d)
                    |> filter(fn: (r) => r["_measurement"] == "venti_param")
		            |> last()
                '''

    result = client.query_api().query(query=query)

    results = []
    for table in result:
        for record in table.records:
            results.append((record.get_time(), record.get_value()))
    
    results2 = []
    names = ['intervall_enable','intervall_on','intervall_time','sdef_hys', 'sdef_on','uschutz_hys','uschutz_on']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)
    

def get_outdoor_values():
    client = get_influxdb_client()

    query = '''from(bucket: "jokley_bucket")
                |> range(start: -1h)
                |> filter(fn: (r) => r["device_name"] == "outdoor00")
                |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" or r["_measurement"] == "device_frmpayload_data_sdef" )
                |> last()
            '''
    result = client.query_api().query(query=query)
   
    results = []
    for table in result:
        for record in table.records:
            results.append(( record.get_value()))
    
    results2 = []
    names = ['humidityOut','sDefOut','temperatureOut','trockenMasseOut']
    results2.append(dict(zip(names,results)))
    dicti={}
    dicti = results2

    client.close()

    return (dicti)

def get_min_max_values():
    client = get_influxdb_client()


    query = '''
            tmin = from(bucket: "jokley_bucket")
                |> range(start: -1h)
                |> filter(fn: (r) => r["device_name"] == "probe01" or r["device_name"] == "probe02")
                |> filter(fn: (r) =>  r["_measurement"] == "device_frmpayload_data_temperature" or r["_measurement"] == "device_frmpayload_data_humidity"  or r["_measurement"] == "device_frmpayload_data_trockenmasse" or r["_measurement"] == "device_frmpayload_data_sdef" )
                |> last()
                |> group(columns: ["_measurement"])
                |> min()

            tmax = from(bucket: "jokley_bucket")
                |> range(start: -1h)
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
    scheduler.add_job(venti_control, 'interval', minutes=5,  replace_existing=True, id='venti_control')
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
    
    
    
@app.route('/download')
def download():
    path = 'debug.log'
    return send_file(path, as_attachment=True)



@app.route('/time')
def time():

    return jsonify(get_time_now(), get_timestamp_now_epoche(),get_timestamp_now(),get_timestamp_now_offset())

@app.route('/influx')
def influx():

    # data = get_min_max_values()
    # humMin = data[0]['humidityMin']
    # humMax = data[0]['humidityMax']
    # sDefMin = data[0]['sDefMin']
    # sDefMax = data[0]['sDefMax']
    # tempMin = data[0]['temperatureMin']
    # tempMax = data[0]['temperatureMax']
    # tsMin = data[0]['trockenMasseMin']
    # tsMax = data[0]['trockenMasseMax']

    # dataOut = get_outdoor_values()
    # humOut = dataOut[0]['humidityOut']
    # sDefOut = dataOut[0]['sDefOut']
    # tempOut = dataOut[0]['temperatureOut']
    # tsOut = dataOut[0]['trockenMasseOut']


    dataVenti = get_venti_control_values()
    startTime = dataVenti[0]['mode'][0]
    mode = dataVenti[0]['mode'][1]
    tsSoll =dataVenti[0]['trockenMasseSoll'][1]
    stock = int(dataVenti[0]['stockaufbau'][1])
    stock *= 3600
    stockini = dataVenti[0]['stockaufbau'][1]

    # dataLastTime = get_venti_lastTimeOn()
    # lastOn = dataLastTime[0]['lastTimeOn']
    
    # DST =  get_timestamp_now_offset()
    # timeNow = get_timestamp_now_epoche()

    # startTimeStock = (startTime + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    # lastTimeOn = (lastOn + timedelta(seconds=DST)).replace(tzinfo=timezone.utc).timestamp() 
    # remainingTimeStock =     int(timeNow - startTimeStock)
    # remainingTimeInterval =  int(timeNow - lastTimeOn)


    iniDict = {'cmd':mode, 'stock':stockini , 'tm':tsSoll} 
  

    return (iniDict)
    #return jsonify('cmd: {}, tm: {}, stock: {}'.format(mode, '0',tsSoll))
    #return jsonify('{},{},{}'.format(sDefMin,sDefMax,sDefOut))
    #return jsonify(dataVenti[0]['mode'][0])
    #return jsonify('{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(humMin, humMax,tempMin,tempMax,tsMin,tsMax,humOut,tempOut,tsOut,startTimeStock,mode,tsSoll,stock))

@app.route('/controlValues')
def controlValues():

    dataVenti = get_venti_control_values()
    startTime = dataVenti[0]['mode'][0]
    mode = dataVenti[0]['mode'][1]
    tsSoll =dataVenti[0]['trockenMasseSoll'][1]
    stockini = dataVenti[0]['stockaufbau'][1]

    iniDict = {'cmd':mode, 'stock':stockini , 'tm':tsSoll} 
    return (iniDict)

@app.route('/controlParamValues')
def controlParamValues():
   
    pramsVenti = get_venti_control_param_values()
    #startTime = pramsVenti[0]['sdef_on'][0]
    sdef_on = pramsVenti[0]['sdef_on'][1]/10
    sdef_hys = pramsVenti[0]['sdef_hys'][1]/10
    uschutz_on = pramsVenti[0]['uschutz_on'][1]/10
    uschutz_hys = pramsVenti[0]['uschutz_hys'][1]/10
    intervall_on =  pramsVenti[0]['intervall_on'][1]/10
    intervall_time =  pramsVenti[0]['intervall_time'][1]/10
    intervall_enable = pramsVenti[0]['intervall_enable'][1]


    iniDict = {'sdef_on':sdef_on, 'sdef_hys':sdef_hys , 'uschutz_on':uschutz_on,  'uschutz_hys':uschutz_hys,'intervall_on':intervall_on,'intervall_time':intervall_time,'intervall_enable':intervall_enable} 
    return (iniDict)

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
            app.logger.info('****************************************')
            app.logger.info('Lüfter Hand ein')
            return jsonify('Venti on')
        elif CMD == 'off':
            venti_cmd(CMD)
            venti_auto(CMD,TM,'0')
            app.logger.info('****************************************')
            app.logger.info('Lüfter Hand aus')
            return jsonify('Venti off')
        elif CMD == 'auto':
            venti_auto(CMD,TM,STOCK)
            venti_control()
            scheduler.reschedule_job('venti_control',  trigger='interval', minutes=5)
            return jsonify('Venti auto')
        else:
            return jsonify('No command send!')
            
    # if request.method == 'GET':
    #     CMD = request.args.get('cmd', default = 'auto', type = str)

    #     if CMD == 'on':
    #         venti_cmd(CMD)
    #         return jsonify('Venti on')
    #     elif CMD == 'off':
    #         venti_cmd(CMD)
    #         return jsonify('Venti off')venti_auto_param
    #     else:
    #         return jsonify('No command send!')
        

@app.route('/ventiParams',methods = ['POST','GET'])
def ventiParams():
    if request.method == 'POST':
        data = request.get_json()
        sdef_on = data['sdef_on']
        sdef_hys = data['sdef_hys']
        uschutz_on = data['uschutz_on']
        uschutz_hys = data['uschutz_hys']
        intervall_on =  data['intervall_on']
        intervall_time =  data['intervall_time']
        intervall_enable = data['intervall_enable']

         
        

        venti_auto_param(sdef_on, sdef_hys,uschutz_on,uschutz_hys,intervall_on,intervall_time,intervall_enable)
        app.logger.info('****************************************')
        app.logger.info('Regelparameter geändert:')
        app.logger.info('SDef on: {}'.format(sdef_on))
        app.logger.info('SDef hys: {}'.format(sdef_hys))
        app.logger.info('ÜSchutz on: {}'.format(uschutz_on))
        app.logger.info('ÜSchutz hys: {}'.format(uschutz_hys))
        app.logger.info('Intervall on: {}'.format(intervall_on))
        app.logger.info('Intervall time: {}'.format(intervall_time))
        app.logger.info('Intervall enable: {}'.format(intervall_enable))
        
        venti_control()

        return jsonify('Regelparameter geändert')



    
    
#if __name__ == "__main__":
    #app.run(host="0.0.0.0",port=5001, debug=True)
