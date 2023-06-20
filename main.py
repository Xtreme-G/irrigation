import utime
import network
import ubinascii
from machine import Pin, Timer  # There are 15 timers available, use carefully!
from functools import partial
from umqtt.simple import MQTTClient
from password import wifi, hivemq
from sensor import MoistureSensor
from observable import ObservableValue, ObservableSum
from pump import Pump
from irrigation import Irrigation


TWENTYFOUR_HOURS_IN_MILLISECONDS = 1_000 * 60 * 60 * 24

pump_config = {
    'pump_duration': 2_000,
    'pump_cooldown': 10_000,
    'pump_cap_time': 1_000 * 100
}
sensor_config = {
    'min_humidity': 0.0,
    'max_humidity': 60.0,
}


buzz = Pin(15, Pin.OUT)
pumps = [Pump(Pin(pin, Pin.OUT), name='Pump') for pin in range(2, 6)]
leds = [Pin(pin, Pin.OUT, value=0) for pin in range(7, 11)]
buttons = [Pin(pin, Pin.IN, machine.Pin.PULL_UP) for pin in range(11, 15)]
sensors = [MoistureSensor(Pin(pin), name='Moisture', period=1000) for pin in range(26, 29)]


# Manual pump control
def start(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=partial(stop, button, pump))
    pump.start()


def stop(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_FALLING, handler=partial(start, button, pump))
    pump.stop()


# To run pump manually usin buttons. Run while button is pressed.
for button, pump in zip(buttons, pumps):
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=partial(start, button, pump))

# WLAN setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi.get('ssid'), wifi.get('password'))
wlan.config(pm=0xa11140)  # PM_POWERSAVE

while not wlan.isconnected():
    utime.sleep(1)
    print('Waiting for connection...')
    
ip = wlan.ifconfig()[0]
print(f'Connected on {ip}')

# MQTT Setup
client = MQTTClient(
    client_id=ubinascii.hexlify(machine.unique_id()),
    server=hivemq.get('server'),
    port=0,
    user=hivemq.get('user'),
    password=hivemq.get('password'),
    keepalive=7200,
    ssl=True,
    ssl_params={'server_hostname': hivemq.get('server')}
)

client.connect()

# Irrigation setup
irrigations = []
irrigations.append(Irrigation('Blueberry', sensors[0], pumps[0], client, **pump_config, **sensor_config, pump_cap_pin=leds[0]))
irrigations.append(Irrigation('Smultron', sensors[1], pumps[1], client, **pump_config, **sensor_config, pump_cap_pin=leds[1]))
irrigations.append(Irrigation('SmallPlants', sensors[2], pumps[2], client, **pump_config, **sensor_config, pump_cap_pin=leds[2]))
irrigations.append(Irrigation('SmallPlants', sensors[2], pumps[3], client, **pump_config, **sensor_config, pump_cap_pin=leds[3]))

# Reset the machine every 24h in order to reset caps
Timer(-1).init(period=TWENTYFOUR_HOURS_IN_MILLISECONDS, mode=Timer.ONE_SHOT, callback=lambda time: machine.reset())

while True:
    machine.idle()
