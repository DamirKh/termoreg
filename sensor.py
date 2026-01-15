# sensor.py – «модель» данных и фоновый опрос
import asyncio
import dht
from machine import Pin

class SensorTask:
    """Опрашивает DHT22 и хранит последние показания."""
    def __init__(self, pin: int, interval: int = 5):
        self._dht = dht.DHT22(Pin(pin))
        self.interval = interval
        self._t = None
        self._h = None

    @property
    def temperature(self):
        return self._t

    @property
    def humidity(self):
        return self._h

    async def run(self):
        while True:
            try:
                self._dht.measure()
                self._t = self._dht.temperature()
                self._h = self._dht.humidity()
            except Exception as exc:
                # можно логировать, у нас пока pass
                pass
            await asyncio.sleep(self.interval)
            