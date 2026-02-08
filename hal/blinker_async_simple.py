import asyncio
from machine import Pin

class Blinker:
    def __init__(self, pin: Pin, interval: float = 0.5):
        self._led = pin
        self.interval = interval
        self._stop = asyncio.Event()
        asyncio.create_task(self._simple_blinker_runner())

    async def _simple_blinker_runner(self):
        on = 1
        while not self._stop.is_set():
            self._led(on)  # зелёный/выкл
            on = 0 if on==1 else 1
            await asyncio.sleep(self.interval)

    def stop(self):
        print("Blinker stopped")
        self._led(0)  # blue when stopped
        self._stop.set()
