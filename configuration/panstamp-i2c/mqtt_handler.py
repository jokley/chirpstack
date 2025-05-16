import os
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import json
from influx import write_to_influx
from i2c_IO import set_relay  # Importing the relay control function

# MQTT Configuration (hardcoded)
MQTT_BROKER = "172.16.238.15"
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "relay/control"
MQTT_TOPIC_STATE = "relay/state"
MQTT_CLIENT_ID = "relay_controller"

# Callback when a message is received
def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        print(f"Received message on topic {message.topic}: {payload}")
        
        # Parse JSON payload, expect {"relay": "on/off", "id": <relay_id>}
        data = json.loads(payload)
        relay_id = data.get("id")
        state = data.get("relay")

        if relay_id is not None and state is not None:
            # Process relay state change (here you would control the relay hardware)
            print(f"Control Relay {relay_id}: {state}")
            # Call set_relay to control the relay
            if state.lower() == 'on':
                set_relay(True)
            elif state.lower() == 'off':
                set_relay(False)
            
            # Save state to InfluxDB
            write_relay_state_to_influx(relay_id, state)
        else:
            print("Invalid message format, expected 'id' and 'relay'.")

    except Exception as e:
        print(f"Error processing message: {e}")

# Write relay state to InfluxDB
def write_relay_state_to_influx(relay_id, state):
    timestamp_s = int(time.time())
    line_protocol = (
        f"relay_state,relay_id={relay_id} state={1 if state.lower() == 'on' else 0} {timestamp_s}"
    )
    write_to_influx(line_protocol)  # Write to InfluxDB

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_COMMAND)

def on_disconnect(client, userdata, rc):
    print(f"Disconnected from MQTT Broker with result code {rc}")

def setup_mqtt():
    # Set up MQTT client
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, callback_api_version=CallbackAPIVersion.V5)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the MQTT broker
    print(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    return client

