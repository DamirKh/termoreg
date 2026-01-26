import asyncio
from neopixel import NeoPixel
from machine import Pin

class Blinker:
    def __init__(self, pin: Pin, interval: float = 0.5):
        self.np = NeoPixel(pin, 1)
        self.interval = interval
        self._stop = asyncio.Event()
        asyncio.create_task(self._neopixel_blinker_runner())

    async def _neopixel_blinker_runner(self):
        on = True
        while not self._stop.is_set():
            self.np[0] = (0, 16, 0) if on else (0, 2, 0)  # зелёный/выкл
            self.np.write()
            on = not on
            await asyncio.sleep(self.interval)


    def stop(self):
        print("Blinker stopped")
        self.np[0] = (0, 0, 16)  # blue when stopped
        self.np.write()
        self._stop.set()
