import os
from influxdb_client import InfluxDBClient, WriteOptions

def get_influxdb_client():
    INFLUXDB_URL = "http://172.16.238.16:8086"
    INFLUXDB_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
    INFLUXDB_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")

    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

def write_to_influx(line_protocol: str):
    BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")
    client = get_influxdb_client()
    write_api = client.write_api(write_options=WriteOptions(batch_size=1))
    
    try:
        write_api.write(bucket=BUCKET, org=client.org, record=line_protocol)
        print("✅ Data written to InfluxDB")
    except Exception as e:
        print(f"❌ Error writing to InfluxDB: {e}")
    finally:
        write_api.__del__()
        client.__del__()
