import asyncio

import time
from machine import Pin, SoftI2C, I2C
from hal.htu21d_mc import HTU21D


# запуск датчика HTU21D
# scl_pin = Pin(22, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
# sda_pin = Pin(23, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
i2c = I2C(1, scl=Pin(4), sda=Pin(5), freq=100000)
htu21d_sensor = HTU21D(i2c, read_delay=10)  # read_delay=60 for normal operation


async def main():
    # ждём первого измерения
    await htu21d_sensor
    print("Первое измерение готово")
    # await htu21d_sensor
    # print("Первое измерение HTU21D готово")

    last_call_time = time.ticks_ms() # <-- Запоминаем время старта

    while True:
        await asyncio.sleep_ms(1000)
        print(f"HTU21D: temp={htu21d_sensor.temperature}, humidity={htu21d_sensor.humidity}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено пользователем")

    # Очистка ресурсов при необходимости