from functools import partial
from machine import Timer
from observable import ObservableValue, ObservableSum, Cooldown
from sensor import Sensor

class Criterion:
    
    """ A Criterion that that can be activated/deactivated and queried is_active and is_valid. """
    
    def __init__(self) -> None:
        pass  # Initialization of only one super class is supported in Micropython.
    
    def is_valid(self) -> bool:
        pass
    
    def is_active(self) -> bool:
        return self._active
    
    def activate(self) -> None:
        self._active = True
          
    def deactivate(self) -> None:
        self._active = False


class ObservableValueCriterion(ObservableValue, Criterion):
    
    def __init__(self,
                 name: str):
        super().__init__(name)
        self.activate()
    
    def is_valid(self) -> bool:
        return self.value
    
    def name(self) -> str:
        return f'ObservableValueCriteion({super().name()})'
    

class ObservingObservableValueCriterion(ObservableValueCriterion):
    
    def __init__(self,
                 observable: Observable,
                 callback: Callable):
        super().__init__(observable.name())
        self._observable = observable
        observable.subscribe(callback)


class SensorCriterion(ObservingObservableValueCriterion):
    
    """ A criterion which validity depends on whether the sensor value is
        inside or outside the specified range. """
    
    def __init__(self,
                 sensor: Sensor,
                 valid_inside_range: bool = True,
                 always_notify: bool = False,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None) -> None:
        self._valid_inside_range = valid_inside_range
        super().__init__(sensor, self.update)
        self._min_value = min_value if min_value is not None else -float('inf')
        self._max_value = max_value if max_value is not None else  float('inf')
        self._always_notify = always_notify
        self.reset()

    def activate(self) -> None:
        super().activate()
        self.reset()
        
    def reset(self) -> None:
        self.value = False

    def update(self, sensor: ObservableValue) -> None:
        if not self.is_active():
            return
        if self._min_value <= sensor.value <= self._max_value:
            value = self._valid_inside_range
        else:
            value = not self._valid_inside_range
        if self.value != value or self._always_notify:
            self.value = value

    def name(self) -> str:
        return f'SensorCriterion({super().name()})'


class CooldownCriterion(ObservingObservableValueCriterion):
    
    """ A criterion that is false during the cooldown period of the Observable. """
    
    def __init__(self,
                 observable: Observable,
                 period: int) -> None:
        super().__init__(observable, partial(self.start, period))
        self.value = True
        
    def start(self, period: int, observable: Observable) -> None:
        Timer(-1).init(period=period, mode=Timer.ONE_SHOT, callback=self.stop)
        self.value = False
        
    def stop(self, time: float) -> None:
        self.value = True
        
    def name(self) -> None:
        return f'CooldownCriterion({super().name()})'
        

class Cap(ObservableValueCriterion):
    
    """ A Criterion which validity depends on if the cap is exceeded. """
    
    def __init__(self, observable_sum: ObservableSum, cap: int) -> None:
        super().__init__(observable_sum.name())
        self.value = True
        self._cap = cap
        self.activate()
        self._observable_sum = observable_sum
        self._observable_sum.subscribe(self.update)
    
    def is_valid(self) -> bool:
        return self.value
    
    def name(self) -> str:
        return f'Cap({super().name()})'
    
    def reset(self, time: Optional[Timer]=None) -> None:
        self._observable_sum.reset()
    
    def update(self, observable: ObservableSum) -> None:
        if (valid := observable.value < self._cap) != self.value:
            self.value = valid
