from machine import ADC, Pin, Timer
from observable import ObservableValue


class Sensor(ObservableValue):

    """ A sensor that measures periodically and transforming the value read from ADC """

    def __init__(self,
                 pin: Pin,
                 name: str,
                 period: int=0) -> None:
        super().__init__(name or str(pin))
        self._pin = ADC(pin)
        if period:
            Timer(period=period, mode=Timer.PERIODIC, callback=self.measure)
    
    def measure(self, time: int):
        self.value = self.transform(self._pin.read_u16())
        
    def transform(self, reading):
        return reading


class MoistureSensor(Sensor):
    
    def __init__(self,
                 pin: Pin,
                 name: Optional[str]=None,
                 period: int=0,
                 min_reading: int=42800,
                 max_reading: int=65535) -> None:
        super().__init__(pin, name, period)
        self._min_reading = min_reading
        self._max_reading = max_reading
        
    def transform(self, reading: int) -> float:
        return 100.0 * (self._max_reading - reading) / (self._max_reading - self._min_reading)
