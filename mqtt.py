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
        observable.subscribe(lambda obs: client.publish(self._topic, str(obs.value), retain=retain, qos=qos))
        observable.subscribe(lambda obs: print(self._topic, obs.value))
