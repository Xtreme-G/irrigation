import utime
import network
import ubinascii
from machine import Pin, Timer
from functools import partial
from umqtt.simple import MQTTClient
from password import wifi, hivemq
from sensor import MoistureSensor
from observable import ObservableValue, ObservableSum
from pump import Pump
from irrigation import Irrigation


def start(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=partial(stop, button, pump))
    pump.start()


def stop(button, pump, pin) -> None:
    button.irq(trigger=machine.Pin.IRQ_FALLING, handler=partial(start, button, pump))
    pump.stop()


buzz = Pin(15, Pin.OUT)
pumps = [Pump(Pin(pin, Pin.OUT, value=1), name=f'Pump{pin}') for pin in range(2, 6)]
leds = [Pin(pin, Pin.OUT) for pin in range(7, 11)]
buttons = [Pin(pin, Pin.IN, machine.Pin.PULL_UP) for pin in range(11, 15)]
sensors = [MoistureSensor(Pin(pin), name=f'Moisture{pin}', period=1000) for pin in [26, 27, 28, 28]]

# To run pump manually usin buttons. Run while button is pressed.
for button, pump in zip(buttons, pumps):
    button.irq(trigger=machine.Pin.IRQ_RISING, handler=partial(start, button, pump))
    
# To display pump cap on LED
def led_cap_callback(led: Pin, cap: int, observable: ObservableSum):
    led.value(observable.value >= cap)

pump_config = {
    'pump_duration': 2_000,
    'pump_cooldown': 10_000,
    'pump_cap_time': 4_000
}

for led, pump in zip(leds, pumps):
    cap = ObservableSum(pump)
    cap.subscribe(partial(led_cap_callback, led, pump_config.get('pump_cap_time', 100_000)))

irrigation = Irrigation('Blåbär', sensors[0], pumps[0], True, **pump_config)
irrigation = Irrigation('Smultron', sensors[1], pumps[1], True, **pump_config)
irrigation = Irrigation('Småkrukor', sensors[2], pumps[2], True, **pump_config)
irrigation = Irrigation('Småkrukor', sensors[3], pumps[3], True, **pump_config)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi.get('ssid'), wifi.get('password'))
wlan.config(pm=0xa11140)  # PM_POWERSAVE

while not wlan.isconnected():
    utime.sleep(1)
    print('Waiting for connection...')
    
ip = wlan.ifconfig()[0]
print(f'Connected on {ip}')


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

#client.connect()

while True:
    machine.idle()
