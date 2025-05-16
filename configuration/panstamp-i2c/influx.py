import os
import logging
from influxdb_client import InfluxDBClient, WriteOptions

# Configure logging
LOG_LEVEL = "INFO"
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("influx_writer")

def get_influxdb_client():
    """
    Create and return an InfluxDB client instance.
    """
    INFLUXDB_URL = "http://172.16.238.16:8086"
    INFLUXDB_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
    INFLUXDB_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
    logger.(f"Connecting to InfluxDB at {INFLUXDB_URL}, org={INFLUXDB_ORG}")
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

def write_to_influx(line_protocol: str):
    """
    Write a raw InfluxDB line protocol string to the specified bucket.
    """
    BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")
    client = get_influxdb_client()
    write_api = client.write_api(write_options=WriteOptions(batch_size=1))
    
    try:
        logger.(f"InfluxDB line protocol to write:\n{line_protocol}")
        write_api.write(bucket=BUCKET, org=client.org, record=line_protocol)
        logger.info("✅ Data written to InfluxDB")
    except Exception as e:
        logger.error(f"❌ Error writing to InfluxDB: {e}")
    finally:
        try:
            write_api.__del__()
            client.__del__()
        except Exception:
            pass
