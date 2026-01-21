from primitives import Switch


class PinInversable():
    def __init__(self, pin, inverted=False):
        self._pin = pin
        self._inverted = inverted

    def value(self):
        return not self._pin.value() if self._inverted else self._pin.value()


class Switch_ladder(Switch):
    """
    Simple switch input device with debounce = 50ms
    and configurable input inversion
    """
    def __init__(self, pin, inverted=False):
        self._pin_inversable = PinInversable(pin, inverted)
        Switch.__init__(self, self._pin_inversable)

    @property
    def ON(self):
        return self()
    
    def __bool__(self):
        return bool(self())
    
    def __str__(self):
        return "ON" if self.ON else "OFF"
