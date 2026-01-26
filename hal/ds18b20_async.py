import asyncio
import time
import onewire
import ds18x20
from machine import Pin


class DS18B20Async:
    """
    Asynchronous DS18B20 HAL driver.
    - Non-blocking
    - Background measurement loop
    - Safe for uasyncio + WiFi
    """

    def __init__(
        self,
        pin: int,
        period_ms: int = 5000,
        resolution: int = 12,
    ):
        self._ow = onewire.OneWire(Pin(pin))
        self._ds = ds18x20.DS18X20(self._ow)
        self._roms = self._ds.scan()

        if not self._roms:
            raise RuntimeError("No DS18B20 sensors found")

        self.period_ms = period_ms
        self.resolution = resolution
        self.conversion_ms = self._resolution_to_ms(resolution)

        self.values = {}        # rom -> temperature
        self.timestamps = {}    # rom -> timestamp

        self._task = asyncio.create_task(self._ds18b20_runner())

    # ---------- public API ----------
    def get(self, rom=None):
        if rom is None:
            return self.values
        return self.values.get(rom)


    # ---------- internals ----------
    async def _ds18b20_runner(self):
        await asyncio.sleep_ms(1000)  # wait for system to stabilize

        while True:
            try:
                # 1. запуск измерения для всех датчиков
                self._ds.convert_temp()
                await asyncio.sleep_ms(self.conversion_ms)

                # 2. чтение каждого датчика
                now = time.time()
                for rom in self._roms:
                    try:
                        temp = self._ds.read_temp(rom)
                        self.values[rom] = temp
                        self.timestamps[rom] = now
                    except Exception:
                        self.values[rom] = None
                    # await asyncio.sleep_ms(0)

            except Exception:
                # общая ошибка шины
                for rom in self._roms:
                    self.values[rom] = None

            await asyncio.sleep_ms(self.period_ms)


    @staticmethod
    def _resolution_to_ms(bits: int) -> int:
        # datasheet values
        return {
            9: 100,
            10: 200,
            11: 400,
            12: 800,
        }.get(bits, 1000)  # default to 1000ms if invalid
