import asyncio
from neopixel import NeoPixel
from machine import Pin

class Blinker:
    def __init__(self, pin: Pin, interval: float = 0.5):
        self.np = NeoPixel(pin, 1)
        self.interval = interval
        self._stop = asyncio.Event()

    async def run(self):
        on = True
        while not self._stop.is_set():
            self.np[0] = (0, 16, 0) if on else (0, 0, 0)  # зелёный/выкл
            self.np.write()
            on = not on
            await asyncio.sleep(self.interval)
        self.np[0] = (0, 0, 16)  # blue when stopped

    def stop(self):
        self._stop.set()
