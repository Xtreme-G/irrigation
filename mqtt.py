from functools import partial


class ObservableValuePublisher:
    
    def __init__(self,
                 client: MQTTClient,
                 observable: ObservableValue,
                 base_topic: str='',
                 retain: bool=False,
                 qos: int=0) -> None:
        self._topic = f'{base_topic}/{observable.name()}'
        self._publisher = partial(self.update, client, self._topic, retain=False, qos=qos)
        observable.subscribe(self.update)
        
    def update(self, observable: Observable) -> None:
        print(self._topic, observable.value)  #self._publisher(observable.value)
