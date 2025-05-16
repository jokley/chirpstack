import os
import time
import serial
from datetime import datetime
from sensor_parser import parse_line
from influx import write_to_influx
from collections import defaultdict
from mqtt_control import setup_mqtt

def main():
    port = "/dev/ttyUSB0"
    baudrate = 38400
    print(f"Started logging from {port} at {baudrate} baud...")

    cache = defaultdict(dict)

    # Setup MQTT Client
    mqtt_client = setup_mqtt()
    mqtt_client.loop_start()  # Start the MQTT loop in a background thread

    with serial.Serial(port, baudrate, timeout=1) as ser:
        while True:
            line = ser.readline().decode(errors='ignore').strip()
            if not line:
                continue

            timestamp_s = int(time.time())  # seconds
            parsed = parse_line(line)
            if not parsed:
                continue

            node = parsed["node"]
            register = parsed["register"]

            # Always keep latest RSSI and LQI
            cache[node]["rssi_dbm"] = parsed["rssi_dbm"]
            cache[node]["lqi"] = parsed["lqi"]

            if register == 0x0C:  # Temperature and Humidity
                cache[node]["temperature_c"] = parsed.get("temperature_c")
                cache[node]["humidity_percent"] = parsed.get("humidity_percent")
                cache[node]["timestamp_s"] = timestamp_s

            elif register == 0x0B:  # Battery
                cache[node]["battery_v"] = parsed.get("battery_v")

            required = ["rssi_dbm", "lqi", "temperature_c", "humidity_percent", "battery_v", "timestamp_s"]
            if all(key in cache[node] for key in required):
                tmp = cache[node]["temperature_c"]
                hum = cache[node]["humidity_percent"]

                # Calculate trockenmasse and sdef
                trockenmasse = -0.0028 * hum**2 + 0.004 * hum + (87 + tmp * 0.2677)
                sdef = ((hum * -0.05) + 5) * math.exp(0.0625 * tmp)

                # Add them to cache
                cache[node]["trockenmasse"] = round(trockenmasse, 2)
                cache[node]["sdef"] = round(sdef, 3)

                line_protocol = (
                    f"device_frmpayload_data_temperature,device_name={node} value={tmp} {timestamp_s}\n"
                    f"device_frmpayload_data_humidity,device_name={node} value={hum} {timestamp_s}\n"
                    f"device_frmpayload_data_trockenmasse,device_name={node} value={cache[node]['trockenmasse']} {timestamp_s}\n"
                    f"device_frmpayload_data_sdef,device_name={node} value={cache[node]['sdef']} {timestamp_s}\n"
                    f"device_frmpayload_data_battery,device_name={node} value={cache[node]['battery_v']} {timestamp_s}\n"
                    f"device_frmpayload_data_rssi,device_name={node} rssi={cache[node]['rssi_dbm']} {timestamp_s}"
                )
                write_to_influx(line_protocol)  # Write to InfluxDB
                cache.pop(node)

if __name__ == "__main__":
    main()
