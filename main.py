import asyncio
from machine import Pin, I2C
from hal.cpu_temp import CpuTemp
from hal.led_task import Blinker
from web_app import build_web_app	# наше веб-приложение

# --------- настройка I2C ----------
# Hardware I2C bus
# There are two hardware I2C peripherals with identifiers 0 and 1. Any available output-capable pins can be used for SCL and SDA but the defaults are given below.

#		I2C(0)	I2C(1)
#scl	18		25
#sda	19		26
#i2c = I2C(0)

# --------- запуск датчика ----------
sensor = CpuTemp(interval=5)

async def main():
    blinker = Blinker(Pin(48, Pin.OUT))
    asyncio.create_task(blinker.run())

    # ждём первого измерения
    await sensor

    # создаём веб-сервер
    web_app = build_web_app(sensor)
    server_task = asyncio.create_task(
        web_app.start_server(host='0.0.0.0', port=80, debug=True)
    )

    # можно добавить другие фоновые задачи
    await server_task          # работаем до отключения

if __name__ == '__main__':
    asyncio.run(main())