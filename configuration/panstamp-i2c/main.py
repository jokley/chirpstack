import asyncio
import serial_asyncio
import logging
import math
import time
from collections import defaultdict
from sensor_parser import parse_line
from influx import write_to_influx
from mqtt_handler import setup_mqtt

LOG_LEVEL = "INFO"
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("panstamp_i2c")

SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 38400

NODE_NAME_MAP = {
    3: "outdoor00",
    17: "probe01",
    25: "probe02"
}

CACHE_TTL_SECONDS = 300  # 5 minutes

class SerialProtocol(asyncio.Protocol):
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.buffer = bytearray()

    def data_received(self, data):
        self.buffer.extend(data)
        while b'\n' in self.buffer:
            line, _, self.buffer = self.buffer.partition(b'\n')
            line_str = line.decode(errors='ignore').strip()
            if line_str:
                try:
                    self.data_queue.put_nowait(line_str)
                except asyncio.QueueFull:
                    logger.warning("⚠️ Serial data queue full, dropping incoming line.")

async def process_queue(data_queue):
    cache = defaultdict(dict)
    mqtt_client = setup_mqtt()
    mqtt_client.loop_start()

    iteration = 0
    while True:
        try:
            line = await asyncio.wait_for(data_queue.get(), timeout=5)
        except asyncio.TimeoutError:
            logger.debug("No serial data received in last 5 seconds.")
            continue

        timestamp_s = int(time.time())
        parsed = parse_line(line)
        logger.info(f"Parsed line: {parsed}")
        if not parsed:
            continue

        node = parsed["node"]
        node_name = NODE_NAME_MAP.get(node, f"node{node}")
        register = parsed["register"]

        cache[node]["rssi_dbm"] = parsed["rssi_dbm"]
        cache[node]["lqi"] = parsed["lqi"]

        if register == 0x0C:
            cache[node]["temperature_c"] = parsed.get("temperature_c")
            cache[node]["humidity_percent"] = parsed.get("humidity_percent")
            cache[node]["timestamp_s"] = timestamp_s
        elif register == 0x0B:
            cache[node]["battery_v"] = parsed.get("battery_v")

        required = ["rssi_dbm", "lqi", "temperature_c", "humidity_percent", "battery_v", "timestamp_s"]
        if all(key in cache[node] for key in required):
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
            logger.info(f"Wrote data for node {node_name} to InfluxDB")
            cache.pop(node)
        else:
            logger.debug(f"Incomplete data for node {node}, skipping Influx write.")

        iteration += 1
        if iteration % 100 == 0:
            # Cache cleanup
            now = time.time()
            to_delete = [node for node, data in cache.items()
                         if 'timestamp_s' in data and now - data['timestamp_s'] > CACHE_TTL_SECONDS]
            for node_to_del in to_delete:
                logger.warning(f"Cleaning up stale cache for node {node_to_del}")
                cache.pop(node_to_del)

async def main():
    data_queue = asyncio.Queue(maxsize=1000)

    loop = asyncio.get_running_loop()
    transport, protocol = await serial_asyncio.create_serial_connection(
        loop, lambda: SerialProtocol(data_queue), SERIAL_PORT, baudrate=BAUDRATE
    )

    await process_queue(data_queue)

if __name__ == "__main__":
    asyncio.run(main())
