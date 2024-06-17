from functools import partial
from machine import Timer


class Observable:
    
    """ An Observable can be subscribed to with a callback that is
        called when notify is called passing along the Observable. 
        Due to the limited callstack depth in MicroPython (30),
        deferred Observables will instead store callbacks in a static
        list for execution at a later stage when appropriate. """   

    deferred_callbacks = []
        
    def __init__(self, name: Optional[str] = None, defer: bool = False) -> None:
        self._name = name
        self._defer = defer
        self._callbacks = []
        
    def name(self) -> str:
        return self._name

    def defer_notifications(self, defer: Optional[bool] = None) -> bool:
        if defer is not None:
            self._defer = defer
        return self._defer
            
    def notify(self, msg=None):
        for callback in self._callbacks:
            if self._defer:
                Observable.deferred_callbacks.append(partial(callback, msg or self))
                #print(f'Deferring a callback, now have {len(Observable.deferred_callbacks)} defered!')
            else:
                callback(msg or self)

    def subscribe(self, callback: Callable) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unsubscribe(self, callback) -> None:
        try:
            self._callbacks.remove(callback)
        except ValueError as e:
            pass
     
    @classmethod 
    def next_callback(cls):
        if cls.deferred_callbacks:
            callback = Observable.deferred_callbacks.pop()  # LIFO
            #print(f'Popped a callback and now have {len(Observable.deferred_callbacks)}')
            callback()
        


class ObservableValue(Observable):
    
    """ A simple value which setter calls notify. """
    
    def __init__(self, name: str, defer: bool = True) -> None:
        super().__init__(name, defer)
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
        super().__init__(observable.name(), observable.defer_notifications())
        self.reset()
        observable.subscribe(self.update)
    
    def name(self) -> str:
        return f'Sum({super().name()})'
    
    def reset(self, time: Optional[int] = None) -> None:
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
        self._timer = Timer(-1)
        
    def subscribe(self, callback) -> None:
        super().subscribe(callback)
        self._observable.subscribe(self._callback)
    
    def unsubscribe(self, callback) -> None:
        super().unsubscribe(callback)
        self._timer.deinit()
        self._observable.unsubscribe(self._callback)
    
    def _start(self, period: int, observable: Observable) -> None:
        self._timer.init(period=period, mode=Timer.ONE_SHOT, callback=self._stop)
        self._observable.unsubscribe(self._callback)
        self.notify(self._observable)
        
    def _stop(self, t: Timer) -> None:
        self._observable.subscribe(self._callback)
