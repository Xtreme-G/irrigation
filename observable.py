from functools import partial
from machine import Timer


class Observable:
    
    """ An Observable can be subscribed to with a callback that is
        called when notify is called passing along the Observable. """

    def __init__(self, name: Optional[str]=None) -> None:
        self._name = name
        self._callbacks = []
 
    def name(self) -> str:
        return self._name
 
    def notify(self, msg=None):
        for callback in self._callbacks:
            callback(msg or self)
 
    def subscribe(self, callback) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)
 
    def unsubscribe(self, callback) -> None:
        try:
            self._callbacks.remove(callback)
        except ValueError as e:
            pass


class ObservableValue(Observable):
    
    """ A simple value which setter calls notify. """
    
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._value = None

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        self._value = value
        self.notify()


class ObservableSum(ObservableValue):
    
    """ Sums the values from setter. """
    
    def __init__(self, observable: ObservableValue) -> None:
        super().__init__(observable.name())
        self.reset()
        observable.subscribe(self.update)
    
    def name(self) -> str:
        return f'Sum({super().name()})'
    
    def reset(self, time: Optional[int]=None) -> None:
        self.value = 0   
        
    def update(self, observable: ObservableValue) -> None:
        self.value += observable.value


class Cooldown(Observable):
    
    """ A wrapper of an Observable if less frequent notifications is desired. """
    
    def __init__(self,
                 observable: Observable,
                 period: int) -> None:
        super().__init__(observable.name())
        self._callback = partial(self._start, period)
        self._observable = observable
        
    def subscribe(self, callback) -> None:
        super().subscribe(callback)
        self._observable.subscribe(self._callback)
    
    def unsubscribe(self, callback) -> None:
        super().unsubscribe(callback)
        self._observable.unsubscribe(self._callback)
    
    def _start(self, period: int, observable: Observable) -> None:
        Timer(-1).init(period=period, mode=Timer.ONE_SHOT, callback=self._stop)
        self._observable.unsubscribe(self._callback)
        self.notify(self._observable)
        
    def _stop(self, time: int) -> None:
        self._observable.subscribe(self._callback)
