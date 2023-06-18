import utime
from controller import Controller
from criteria import Cap, CooldownCriterion, SensorCriterion
from functools import partial
from observable import Cooldown, ObservableSum, ObservableValue
from mqtt import ObservableValuePublisher


class Irrigation(ObservableValue):
    
    """ Irrigation system with a moisture sensor holding the humidity level
        within the range [min_humidity, max_humidity] by running the pump
        in the watering state and waiting in the draining stage.
        
        Publishes sensor values, pump time, and state to an MQTT client. """
    
    def __init__(self,
                 name: str,
                 sensor: Sensor,
                 pump: Pump,
                 mqtt_client: Optional[MQTTClient]=None,
                 min_humidity=0.0,
                 max_humidity=60.0,
                 pump_duration=2_000,
                 pump_cooldown=10_000,
                 pump_cap_time=100_000) -> None:
        super().__init__(name)
        self._pump = pump
        self._controller = Controller()
        
        # Water up to max_value, drain until max_max value is reached
        self._watering_criterion = SensorCriterion(sensor, max_value=max_humidity)
        self._draining_criterion = SensorCriterion(sensor, max_value=min_humidity)
        self._controller.add_criterion(self._watering_criterion)
        self._controller.add_criterion(self._draining_criterion)
        
        #  Run pump for short spurts with cooldown in between. Cap the total runtime for safety.
        self._controller.add_criterion(CooldownCriterion(pump, pump_cooldown))
        self._controller.add_criterion(Cap(pump, pump_cap_time))
        
        # Switch between watering/draining states
        self._watering_callback = self._watering  # Micropython does not implement 3.8+ behavior for equality of member functions
        self._draining_callback = self._draining
        self._pump_callback = partial(self._start_pump, pump_duration)
              
        if mqtt_client:
            ObservableValuePublisher(mqtt_client, Cooldown(sensor, 15 * 60 * 1_000), base_topic=name)
            ObservableValuePublisher(mqtt_client, ObservableSum(pump), base_topic=name)
            ObservableValuePublisher(mqtt_client, self, base_topic=name)
            
        self._draining(self._controller)  # start in draining state
        utime.sleep(2)                    # Do not start everything simultaneously

    def _watering(self, observable) -> None:
        self._watering_criterion.activate()
        self._draining_criterion.deactivate()
        self._draining_criterion.unsubscribe(self._watering_callback)
        self._watering_criterion.subscribe(self._draining_callback)
        self._pump_callback(None)
        self._controller.subscribe(self._pump_callback)
        self.value = 'Watering'
        
    def _draining(self, observable) -> None:
        self._watering_criterion.deactivate()
        self._draining_criterion.activate()
        self._watering_criterion.unsubscribe(self._draining_callback)
        self._draining_criterion.subscribe(self._watering_callback)
        self._controller.unsubscribe(self._pump_callback)
        self.value = 'Draining'
        
    def _start_pump(self, period: int=2_000, observable: Optional[Observable]=None) -> None:
        self._pump.start(period)
