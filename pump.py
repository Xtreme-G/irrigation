import utime
from machine import Pin, Timer
from observable import ObservableValue


class Pump(ObservableValue):
    
    def __init__(self,
                 pin: Pin,
                 name: Optional[str]=None) -> None:
        super().__init__(name or str(pin))
        self._pin = pin
        self._timer = Timer(-1)
        self.stop()
        
    def start(self, period: int=0) -> None:
        if self.isrunning():
            return
        self._pin.off()  # Relay module operates this way.
        self.value = period
        if period:
            self._timer.init(period=period, mode=Timer.ONE_SHOT, callback=self.stop)
        
    def stop(self, t: Optional[Timer]=None) -> None:
        self._timer.deinit()
        self._pin.on()  # Relay module operates this way.
        
    def isrunning(self) -> bool:
        return not self._pin.value()
