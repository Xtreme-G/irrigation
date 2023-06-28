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
                 min_humidity: float=0.0,
                 max_humidity: float=60.0,
                 sensor_cooldown_period_watering: int=1_000*60,
                 sensor_cooldown_period_draining: int=1_000*15*60,
                 pump_duration: int=2_000,
                 pump_cooldown: int=10_000,
                 pump_cap_time: int=100_000,
                 pump_cap_pin: Optional[Pin]=None) -> None:
        super().__init__(name)
        self._pump = pump
        self._pump_counter = ObservableSum(pump)
        self._controller = Controller()
        self._mqtt_client = mqtt_client
        
        # Water up to max_value, drain until max_max value is reached
        self._watering_criterion = SensorCriterion(sensor, max_value=max_humidity)
        self._draining_criterion = SensorCriterion(sensor, max_value=min_humidity)
        self._controller.add_criterion(self._watering_criterion)
        self._controller.add_criterion(self._draining_criterion)
		# Polling criterion for the controller, always valid.
        self._controller.add_criterion(SensorCriterion(sensor, notify_state_change_only=False))
        
        #  Run pump for short spurts with cooldown in between.
        #  Cap the total runtime for safety. Reset the cap daily.
        self._cap = Cap(self._pump_counter, pump_cap_time)
        self._controller.add_criterion(self._cap)
        if pump_cooldown:
            self._controller.add_criterion(CooldownCriterion(pump, pump_cooldown))
        if pump_cap_pin:
            self._cap.subscribe(lambda obs: pump_cap_pin.value(not obs.value))
        
        # Switch between watering/draining states
        self._watering_callback = self._watering  # Micropython does not implement 3.8+ behavior for equality of member functions
        self._draining_callback = self._draining
        self._pump_callback = partial(self._start_pump, pump_duration)
              
        self._pump_publisher = ObservableValuePublisher(mqtt_client, self._pump_counter, base_topic=name)
        self._state_publisher = ObservableValuePublisher(mqtt_client, self, base_topic=name)
        self._sensor_publisher_watering = ObservableValuePublisher(mqtt_client, Cooldown(sensor, sensor_cooldown_period_watering), base_topic=name)
        self._sensor_publisher_draining = ObservableValuePublisher(mqtt_client, Cooldown(sensor, sensor_cooldown_period_draining), base_topic=name)
            
        self._draining(self._controller)  # start in draining state
        utime.sleep_ms(1000)              # Do not start everything simultaneously

    def name(self) -> str:
        return self._name

    def _watering(self, observable) -> None:
        self._sensor_publisher_draining.deactivate()
        self._sensor_publisher_watering.activate()
        self._watering_criterion.activate()
        self._draining_criterion.deactivate()
        self._draining_criterion.unsubscribe(self._watering_callback)
        self._watering_criterion.subscribe(self._draining_callback)
        self._controller.subscribe(self._pump_callback)
        self.value = 'Watering'
        
    def _draining(self, observable) -> None:
        self._sensor_publisher_watering.deactivate()
        self._sensor_publisher_draining.activate()
        self._watering_criterion.deactivate()
        self._draining_criterion.activate()
        self._watering_criterion.unsubscribe(self._draining_callback)
        self._draining_criterion.subscribe(self._watering_callback)
        self._controller.unsubscribe(self._pump_callback)
        self.value = 'Draining'
    
    def _start_pump(self, period: int=2_000, observable: Optional[Observable]=None) -> None:
        self._pump.start(period)
        