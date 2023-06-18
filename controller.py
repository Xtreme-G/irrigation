from observable import Observable


class Controller(Observable):
    
    """ A controller that notifies when all active critiera are met. """
    
    def __init__(self) -> None:
        super().__init__('Controller')
        self._criteria = []
        self._callback = self.update  # Micropython does not implement 3.8+ behavior for equality of member functions
        
    def add_criterion(self, criterion: Criterion) -> None:
        criterion.subscribe(self._callback)
        self._criteria.append(criterion)  
        
    def remove_criteriea(self, criterion: Criterion) -> None:
        criterion.unsubscribe(self._callback)
        try:
            self._criteria.remove(criterion)
        except ValueError:
            pass
        
    def update(self, observable: Observable) -> None:
        if all([criterion.isvalid() for criterion in self._criteria if criterion.isactive()]):
            self.notify()
    