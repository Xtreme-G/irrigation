from functools import partial


class ObservableValuePublisher:
    
    """ MQTT publisher for ObservableValues. """
    
    def __init__(self,
                 client: MQTTClient,
                 observable: ObservableValue,
                 base_topic: str='',
                 retain: bool=False,
                 qos: int=0) -> None:
        self._topic = f'{base_topic}/{observable.name()}'
        self._observable = observable
        self._publish_callback = lambda obs: client.publish(self._topic, str(obs.value), retain=retain, qos=qos) if client else lambda obs: None
        self._print_callback = lambda obs: print(self._topic, obs.value)
        self.activate()
        
    def __del__(self) -> None:
            self.deactivate()
        
    def activate(self) -> None:
        self._observable.subscribe(self._publish_callback)
        self._observable.subscribe(self._print_callback)
        
    def deactivate(self) -> None:
        self._observable.unsubscribe(self._publish_callback)
        self._observable.unsubscribe(self._print_callback)
