import smbus2

bus = smbus2.SMBus(1)
PCF8574_ADDR = 0x20

# Cached relay state so we can modify individual bits
current_state = 0xFF  # start with all OFF (all bits high)

def set_relay(relay_id: int, state: bool):
    """
    Set individual relay state on PCF8574.
    relay_id: 1–8 (maps to bit 0–7)
    state: True to turn ON, False to turn OFF
    """
    global current_state

    bit = 1 << (relay_id - 1)

    if state:
        # Turn ON relay => set bit LOW (clear)
        current_state &= ~bit
    else:
        # Turn OFF relay => set bit HIGH (set)
        current_state |= bit

    bus.write_byte(PCF8574_ADDR, current_state)
