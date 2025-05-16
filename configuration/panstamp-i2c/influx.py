import os
import logging
from influxdb_client import InfluxDBClient, WritePrecision

logger = logging.getLogger("influx")

# Load environment variables using the same names as in your .env file
url = "http://172.16.238.16:8086"
token = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
org = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
bucket = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")

def write_to_influx(line_protocol: str):
    logger.info(f"[influx] Connecting to InfluxDB at {url}, org={org}")
    logger.info("[influx] InfluxDB line protocol to write:\n%s", line_protocol)

    try:
        with InfluxDBClient(url=url, token=token, org=org) as client:
            write_api = client.write_api()
            write_api.write(
                bucket=bucket,
                org=org,
                record=line_protocol,
                write_precision=WritePrecision.S,
            )
        logger.info("[influx] ✅ Data written to InfluxDB")
    except Exception as e:
        logger.error(f"[influx] ❌ Failed to write to InfluxDB: {e}")
        
