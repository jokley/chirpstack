import smbus2

bus = smbus2.SMBus(1)  # This assumes you're using the Raspberry Pi I2C bus 1
PCF8574_ADDR = 0x20  # Address of the PCF8574 I/O expander

def set_relay(state: bool):
    """
    Control the relay state via the PCF8574 I/O expander.
    :param state: True to turn on, False to turn off.
    """
    value = 0x00 if state else 0xFF  # 0x00 turns the relay on, 0xFF turns it off
    bus.write_byte(PCF8574_ADDR, value)  # Write to the I2C bus
