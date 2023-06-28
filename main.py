import utime
import network
import ubinascii
from machine import Pin, Timer  # There are 15 timers available, use carefully!
from functools import partial
from umqtt.simple import MQTTClient
from mqtt import Receiver
from password import wifi, hivemq, sensor_config
from sensor import MoistureSensor
from observable import ObservableValue, ObservableSum
from pump import Pump
from irrigation import Irrigation


# Reset the machine every 24h in order to reset caps
TWENTYFOUR_HOURS_IN_MILLISECONDS = 1_000 * 60 * 60 * 24
Timer(-1).init(period=TWENTYFOUR_HOURS_IN_MILLISECONDS, mode=Timer.ONE_SHOT, callback=lambda time: machine.reset())


pump_config = {
    'pump_duration': 5_000,
    'pump_cooldown': 0,
    'pump_cap_time': 1_000 * 200
}
humidity_config = {
    'min_humidity': 30.0,
    'max_humidity': 75.0,
    'sensor_cooldown_period_watering': 1_000 * 15,
    'sensor_cooldown_period_draining': 1_000 * 5 * 60
}

buzz = Pin(15, Pin.OUT)
pumps = [Pump(Pin(pin, Pin.OUT), name=f'Pump') for pin in range(2, 6)]
leds = [Pin(pin, Pin.OUT, value=0) for pin in range(7, 11)]
buttons = [Pin(pin, Pin.IN, machine.Pin.PULL_UP) for pin in range(11, 15)]
sensors = [MoistureSensor(Pin(pin), name='Moisture', period=1_000, **sensor_config) for pin in range(26, 29)]


# Manual pump control
def start(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=partial(stop, button, pump))
    pump.start()


def stop(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_FALLING, handler=partial(start, button, pump))
    pump.stop()


# To run pump manually usin buttons. Run while button is pressed.
# WARNING! When the pump is connected to the relay module, it seems to cause transients
# triggering IRQ_FALLING and IRQ_RISING. Thus this cannot be used
for button, pump in zip(buttons, pumps):
    pass
    #button.irq(trigger=machine.Pin.IRQ_FALLING, handler=partial(start, button, pump))

# WLAN setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi.get('ssid'), wifi.get('password'))
wlan.config(pm=0xa11140)  # PM_POWERSAVE

# MQTT Setup
client = MQTTClient(
    client_id=ubinascii.hexlify(machine.unique_id()),
    server=hivemq.get('server'),
    port=0,
    user=hivemq.get('user'),
    password=hivemq.get('password'),
    keepalive=600,
    ssl=True,
    ssl_params={'server_hostname': hivemq.get('server')}
)
receiver = Receiver(client)

for i in range(10):
    utime.sleep(1)
    print('Waiting for connection...')
    if wlan.isconnected():
        break
    
if not wlan.isconnected():
    client = None
else:
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    status = client.connect()
    print(f'MQTT client connected with status {status}')

# Irrigation setup
irrigations = []
irrigations.append(Irrigation('Blueberry', sensors[0], pumps[0], client, **pump_config, **humidity_config, pump_cap_pin=leds[0]))
irrigations.append(Irrigation('Smultron', sensors[1], pumps[1], client, **pump_config, **humidity_config, pump_cap_pin=leds[1]))
irrigations.append(Irrigation('Cucumber', sensors[2], pumps[2], client, **pump_config, **humidity_config, pump_cap_pin=leds[2]))
irrigations.append(Irrigation('Zinnia', sensors[2], pumps[3], client, **pump_config, **humidity_config, pump_cap_pin=leds[3]))

for irr in irrigations:
    topic = bytes(f'{irr.name()}/Pump', 'utf-8')
    receiver.subscribe(topic, lambda msg, irr=irr: irr._start_pump(int(msg.decode('utf-8'))))  # Force capture of irr


while True:
    machine.idle()
    client.check_msg()
