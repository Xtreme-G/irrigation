from functools import partial
from machine import Timer
from observable import ObservableValue, ObservableSum
from sensor import Sensor

class Criterion:
    
    """ A Criterion that that can be quries isactive and isvalid. """
    
    def __init__(self) -> None:
        pass  # Initialization of only one super class is supported in Micropython.
    
    def isvalid(self) -> bool:
        pass
    
    def isactive(self) -> bool:
        return self._active
    
    def activate(self) -> None:
        self._active = True
          
    def deactivate(self) -> None:
        self._active = False


class ObservableValueCriterion(ObservableValue, Criterion):
    
    def __init__(self, name: str):
        super().__init__(name)
        self.activate()
    
    def isvalid(self) -> bool:
        return self.value
    
    def name(self) -> str:
        return f'ObservableValueCriteion({super().name()})'
        
  
class SensorCriterion(ObservableValueCriterion):
    
    """ A criterion which validity depends on whether the sensor value is
        inside or outside the specified range. """
    
    def __init__(self,
                 sensor: Sensor,
                 valid_inside_range: bool=True,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None) -> None:
        super().__init__(sensor.name())
        sensor.subscribe(self.update)
        self._min_value = min_value if min_value is not None else -float('inf')
        self._max_value = max_value if max_value is not None else  float('inf')
        self._valid_inside_range = valid_inside_range
        
    def update(self, sensor: ObservableValue) -> None:
        if self._min_value <= sensor.value <= self._max_value:
            value = self._valid_inside_range
        else:
            value = not self._valid_inside_range
        if self.value != value:
            self.value = value


class CooldownCriterion(ObservableValueCriterion):
    
    """ A criterion that is false during the cooldown period of the Observable. """
    
    def __init__(self,
                 observable: Observable,
                 period: int) -> None:
        super().__init__(observable.name())
        self.value = True
        self._timer = Timer(-1)
        observable.subscribe(partial(self.start, period))
        
    def start(self, period: int, observable: Observable,) -> None:
        self._timer.init(period=period, mode=Timer.ONE_SHOT, callback=self.stop)
        self.value = False
        
    def stop(self, time: float) -> None:
        self.value = True
        

class Cap(ObservableSum, Criterion):
    
    """ A Criterion which validity depends on if the cap is met. """
    
    def __init__(self, observable: ObservableValue, cap: int) -> None:
        super().__init__(observable)
        self._cap = cap
        self.activate()
    
    def name(self) -> str:
        return f'Cap({super().name()})'
    
    def isvalid(self) -> bool:
        return self.value < self._cap
