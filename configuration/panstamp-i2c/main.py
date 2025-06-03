import os
import time
import serial
import math
import logging
import threading
from datetime import datetime
from queue import Queue, Full, Empty
from collections import defaultdict

from sensor_parser import parse_line
from influx import write_to_influx
from mqtt_handler import setup_mqtt

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("panstamp_i2c")

# Global constants
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 38400
QUEUE_MAXSIZE = 1000
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_CLEANUP_INTERVAL = 3000  # seconds

NODE_NAME_MAP = {
    3: "outdoor00",
    17: "probe01",
    25: "probe02"
}

def read_serial(serial_port, baudrate, data_queue):
    """ Continuously read lines from serial and enqueue them. """
    try:
        with serial.Serial(serial_port, baudrate, timeout=1) as ser:
            while True:
                line = ser.readline().decode(errors='ignore').strip()
                if line:
                    try:
                        data_queue.put(line, timeout=1)
                    except Full:
                        logger.warning("⚠️ Serial data queue full, dropping incoming line.")
                        time.sleep(0.1)
                else:
                    time.sleep(0.01)  # Throttle loop if no data
    except serial.SerialException as e:
        logger.error(f"Serial port error: {e}")
    except Exception:
        logger.exception("Unexpected error in serial reader thread.")

def cleanup_cache(cache):
    now = time.time()
    stale = [node for node, data in cache.items()
             if 'timestamp_s' in data and now - data['timestamp_s'] > CACHE_TTL_SECONDS]
    for node in stale:
        logger.info(f"🧹 Cleaning up stale cache for node {node}")
        cache.pop(node)

def process_line(line, cache, mqtt_client):
    try:
        parsed = parse_line(line)
    except Exception as e:
        logger.debug(f"Parsing failed: {e}")
        return

    if not parsed:
        return

    logger.debug(f"Parsed: {parsed}")

    node = parsed["node"]
    node_name = NODE_NAME_MAP.get(node, f"node{node}")
    register = parsed["register"]
    timestamp_s = int(time.time())

    cache[node]["rssi_dbm"] = parsed.get("rssi_dbm")
    cache[node]["lqi"] = parsed.get("lqi")

    if register == 0x0C:
        cache[node]["temperature_c"] = parsed.get("temperature_c")
        cache[node]["humidity_percent"] = parsed.get("humidity_percent")
        cache[node]["timestamp_s"] = timestamp_s
    elif register == 0x0B:
        cache[node]["battery_v"] = parsed.get("battery_v")

    required = ["rssi_dbm", "lqi", "temperature_c", "humidity_percent", "battery_v", "timestamp_s"]
    if all(k in cache[node] for k in required):
        tmp = cache[node]["temperature_c"]
        hum = cache[node]["humidity_percent"]

        trockenmasse = -0.0028 * hum**2 + 0.004 * hum + (87 + tmp * 0.2677)
        sdef = ((hum * -0.05) + 5) * math.exp(0.0625 * tmp)

        cache[node]["trockenmasse"] = round(trockenmasse, 2)
        cache[node]["sdef"] = round(sdef, 3)

        line_protocol = (
            f"device_frmpayload_data_temperature,device_name={node_name} value={tmp} {timestamp_s}\n"
            f"device_frmpayload_data_humidity,device_name={node_name} value={hum} {timestamp_s}\n"
            f"device_frmpayload_data_trockenmasse,device_name={node_name} value={cache[node]['trockenmasse']} {timestamp_s}\n"
            f"device_frmpayload_data_sdef,device_name={node_name} value={cache[node]['sdef']} {timestamp_s}\n"
            f"device_frmpayload_data_battery,device_name={node_name} value={cache[node]['battery_v']} {timestamp_s}\n"
            f"device_frmpayload_data_rssi,device_name={node_name} rssi={cache[node]['rssi_dbm']} {timestamp_s}"
        )

        write_to_influx(line_protocol)
        logger.info(f"✅ Wrote data for {node_name}")
        cache.pop(node)
    else:
        logger.debug(f"Partial data for node {node}, waiting for more.")

def main():
    logger.info(f"🚀 Starting serial logger on {SERIAL_PORT} @ {BAUDRATE} baud")

    cache = defaultdict(dict)
    data_queue = Queue(maxsize=QUEUE_MAXSIZE)
    mqtt_client = setup_mqtt()
    mqtt_client.loop_start()

    threading.Thread(target=read_serial, args=(SERIAL_PORT, BAUDRATE, data_queue), daemon=True).start()

    last_cache_cleanup = time.time()

    try:
        while True:
            try:
                line = data_queue.get(timeout=5)
                process_line(line, cache, mqtt_client)
            except Empty:
                logger.debug("Waiting for serial data...")
            
            if time.time() - last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
                cleanup_cache(cache)
                last_cache_cleanup = time.time()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping gracefully...")
        mqtt_client.loop_stop()

if __name__ == "__main__":
    main()
