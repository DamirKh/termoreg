import esp32
import asyncio

class CpuTemp:
    """Псевдо-сенсор: температура кристалла ESP32."""
    def __init__(self, interval: int = 5):
        self.interval = interval
        self.temperature = None
        self.humidity = None   # заглушка, всегда None
        asyncio.create_task(self._esp32temperature_sensor())

    async def _esp32temperature_sensor(self):
        while True:
            self.temperature = esp32.mcu_temperature()
            await asyncio.sleep(self.interval)

    def __iter__(self):               # совместимость с HTU21D
        while self.temperature is None:
            yield from asyncio.sleep(0)
